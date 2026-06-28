"""Tests for backward-compatible dashboard routes."""

from __future__ import annotations

import skillreg.config as cfgmod
from fastapi.testclient import TestClient

from skillreg.server import create_app


def _client():
    return TestClient(create_app())


def _make_workspace(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    skill_dir = workspace / "skills" / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: Compat test\n---\n\n# my-skill\n",
        encoding="utf-8",
    )
    (skill_dir / "notes.md").write_text("compat hello\n", encoding="utf-8")

    target = tmp_path / "target" / "skills"
    target.mkdir(parents=True)

    cfg_path = tmp_path / "config.json"
    monkeypatch.setattr(cfgmod, "CONFIG_FILE", cfg_path)
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", cfg_path.parent)
    cfg = cfgmod.load_config()
    cfg.workspace_path = str(workspace)
    cfg.targets = [str(target)]
    cfgmod.save_config(cfg)
    return workspace, target


def test_compat_routes_cover_dashboard_legacy_paths(tmp_path, monkeypatch):
    _workspace, target = _make_workspace(tmp_path, monkeypatch)
    client = _client()

    sync_resp = client.post("/api/sync/execute", json={"target": str(target)})
    assert sync_resp.status_code == 200
    assert sync_resp.json()["success"] is True

    tree_resp = client.get("/api/skill-tree", params={"skill": "my-skill"})
    assert tree_resp.status_code == 200
    assert tree_resp.json()["type"] == "dir"

    file_resp = client.get("/api/skill-file", params={"skill": "my-skill", "path": "notes.md"})
    assert file_resp.status_code == 200
    assert file_resp.json()["content"] == "compat hello\n"

    targets_resp = client.get("/api/skill-sync-targets")
    assert targets_resp.status_code == 200
    assert targets_resp.json()[0]["path"] == str(target)

    refresh_resp = client.get("/api/refresh-data")
    assert refresh_resp.status_code == 200
    assert any(skill["name"] == "my-skill" for skill in refresh_resp.json()["skills"])

    target_file_resp = client.get(
        "/api/skill-target-file",
        params={"skill": "my-skill", "target": str(target), "path": "notes.md"},
    )
    assert target_file_resp.status_code == 200
    assert target_file_resp.json()["content"] == "compat hello\n"

    presence_resp = client.get("/api/skill-target-presence", params={"skill": "my-skill"})
    assert presence_resp.status_code == 200
    assert presence_resp.json()["targets"][str(target)] == "synced"

    diff_resp = client.get("/api/skill-diff", params={"skill": "my-skill", "target": str(target)})
    assert diff_resp.status_code == 200
    assert all(row["status"] == "unchanged" for row in diff_resp.json())

    target_skills_resp = client.get("/api/target-skills", params={"target": str(target)})
    assert target_skills_resp.status_code == 200
    assert target_skills_resp.json()["skills"][0]["name"] == "my-skill"

    remove_resp = client.post(
        "/api/remove-skill-from-target",
        params={"skill": "my-skill", "target": str(target), "force": "true"},
    )
    assert remove_resp.status_code == 200
    assert remove_resp.json()["removed"] is True

    legacy_sync_resp = client.post("/api/sync-skills", params={"target": str(target)})
    assert legacy_sync_resp.status_code == 200
    assert legacy_sync_resp.json()["success"] is True
