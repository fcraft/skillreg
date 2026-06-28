"""E2E-style API coverage for dashboard migration workflow."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import skillreg.config as cfgmod
from fastapi.testclient import TestClient

from skillreg.server import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def _make_workspace(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "workspace"
    skills_dir = workspace / "skills"
    skills_dir.mkdir(parents=True)
    skill_dir = skills_dir / "demo-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: Demo skill\n---\n\n# demo\n",
        encoding="utf-8",
    )
    (skill_dir / "notes.md").write_text("hello dashboard migration\n", encoding="utf-8")
    nested = skill_dir / "docs"
    nested.mkdir()
    (nested / "guide.txt").write_text("guide\n", encoding="utf-8")

    cfg_path = tmp_path / "config.json"
    monkeypatch.setattr(cfgmod, "CONFIG_FILE", cfg_path)
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", cfg_path.parent)
    cfg = cfgmod.load_config()
    cfg.workspace_path = str(workspace)
    target_path = tmp_path / "targets" / "claude-skills"
    target_path.mkdir(parents=True)
    cfg.targets = [str(target_path)]
    cfgmod.save_config(cfg)
    return workspace, target_path


def test_dashboard_migration_sync_workflow_e2e(tmp_path, monkeypatch):
    workspace, target_path = _make_workspace(tmp_path, monkeypatch)
    client = _client()

    tree_resp = client.get("/api/skills/demo-skill/tree")
    assert tree_resp.status_code == 200
    tree = tree_resp.json()
    assert tree["type"] == "dir"
    assert any(child["name"] == "SKILL.md" for child in tree["children"])

    file_resp = client.get("/api/skills/demo-skill/file", params={"path": "notes.md"})
    assert file_resp.status_code == 200
    assert file_resp.json()["content"] == "hello dashboard migration\n"

    export_resp = client.get("/api/skills/demo-skill/export")
    assert export_resp.status_code == 200
    assert export_resp.headers["content-disposition"] == 'attachment; filename="demo-skill.zip"'
    with zipfile.ZipFile(io.BytesIO(export_resp.content)) as archive:
        assert sorted(archive.namelist()) == ["SKILL.md", "docs/guide.txt", "notes.md"]

    config_resp = client.get("/api/sync/config")
    assert config_resp.status_code == 200
    assert config_resp.json()["targets"][0]["path"] == str(target_path)

    status_before = client.get("/api/sync/status")
    assert status_before.status_code == 200
    assert status_before.json()[0]["status"] == "missing"

    sync_resp = client.post("/api/sync/execute", json={"target": str(target_path)})
    assert sync_resp.status_code == 200
    assert sync_resp.json()["success"] is True
    assert (target_path / "demo-skill" / "notes.md").read_text(encoding="utf-8") == "hello dashboard migration\n"

    presence_resp = client.get("/api/sync/skill-presence", params={"skill": "demo-skill"})
    assert presence_resp.status_code == 200
    assert presence_resp.json()["targets"][str(target_path)] == "synced"

    target_skills_resp = client.get("/api/sync/target-skills", params={"target": str(target_path)})
    assert target_skills_resp.status_code == 200
    target_skills = target_skills_resp.json()["skills"]
    assert target_skills[0]["name"] == "demo-skill"
    assert target_skills[0]["managed"] is True

    target_file_resp = client.get(
        "/api/sync/target-file",
        params={"skill": "demo-skill", "target": str(target_path), "path": "notes.md"},
    )
    assert target_file_resp.status_code == 200
    assert target_file_resp.json()["content"] == "hello dashboard migration\n"

    (target_path / "demo-skill" / "notes.md").write_text("drifted content\n", encoding="utf-8")
    diff_resp = client.get("/api/sync/diff", params={"skill": "demo-skill", "target": str(target_path)})
    assert diff_resp.status_code == 200
    assert {"path": "notes.md", "status": "modified"} in diff_resp.json()

    status_after_drift = client.get("/api/sync/status", params={"skill": "demo-skill"})
    assert status_after_drift.status_code == 200
    assert status_after_drift.json()[0]["status"] == "modified"

    remove_resp = client.post(
        "/api/sync/remove-skill",
        json={"skill": "demo-skill", "target": str(target_path), "force": True},
    )
    assert remove_resp.status_code == 200
    assert remove_resp.json()["removed"] is True
    assert not (target_path / "demo-skill").exists()

    project_resp = client.post(
        "/api/sync/projects",
        json={"name": "demo-project", "targets": [str(target_path)]},
    )
    assert project_resp.status_code == 200
    project_id = project_resp.json()["project"]["id"]

    exec_project_resp = client.post(
        "/api/sync/execute",
        json={"project": project_id, "skills": ["demo-skill"]},
    )
    assert exec_project_resp.status_code == 200
    assert exec_project_resp.json()["project"] == "demo-project"
    assert exec_project_resp.json()["results"][0]["success"] is True
    assert (target_path / "demo-skill" / "SKILL.md").is_file()

    project_status_resp = client.get("/api/sync/status", params={"include_projects": "true", "skill": "demo-skill"})
    assert project_status_resp.status_code == 200
    assert any(row.get("_project") == "demo-project" for row in project_status_resp.json())


def test_sync_target_rename_and_remove_support_absolute_paths(tmp_path, monkeypatch):
    _workspace, target_path = _make_workspace(tmp_path, monkeypatch)
    client = _client()

    extra_target = tmp_path / "targets" / "codex-skills"
    add_resp = client.post("/api/sync/targets", json={"name": "codex", "path": str(extra_target)})
    assert add_resp.status_code == 200

    renamed_target = tmp_path / "targets" / "codex-renamed"
    rename_resp = client.put(
        f"/api/sync/targets/{extra_target}/rename",
        json={"newName": str(renamed_target)},
    )
    assert rename_resp.status_code == 200
    assert rename_resp.json()["target"]["path"] == str(renamed_target)

    remove_resp = client.delete(f"/api/sync/targets/{renamed_target}")
    assert remove_resp.status_code == 200
    assert remove_resp.json()["removed"] == str(renamed_target)
