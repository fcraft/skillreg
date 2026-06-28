"""Tests for skills and sync API endpoints."""

from __future__ import annotations

from pathlib import Path

import skillreg.config as cfgmod
from skillreg.server import create_app
from skillreg.server import health as health_api
from skillreg.server import submodules as submodules_api


def _client():
    from fastapi.testclient import TestClient
    return TestClient(create_app())


def _use_temp_config(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.json"
    monkeypatch.setattr(cfgmod, "CONFIG_FILE", cfg_path)
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", cfg_path.parent)
    monkeypatch.setattr(health_api, "CONFIG_FILE", cfg_path)
    return cfg_path


def _make_workspace(tmp_path, monkeypatch):
    """Create a mock workspace and configure it."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    skill_dir = skills_dir / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: Test\n---\n\n# my-skill\n",
        encoding="utf-8",
    )

    _use_temp_config(tmp_path, monkeypatch)
    cfg = cfgmod.load_config()
    cfg.workspace_path = str(tmp_path)
    cfgmod.save_config(cfg)
    return tmp_path


def test_skills_list_lite(tmp_path, monkeypatch):
    """GET /api/skills returns lightweight list."""
    _make_workspace(tmp_path, monkeypatch)
    client = _client()
    r = client.get("/api/skills")
    assert r.status_code == 200
    data = r.json()
    assert "skills" in data
    assert "generatedAt" in data
    assert "repoNodes" not in data  # lite mode


def test_skills_list_full(tmp_path, monkeypatch):
    """GET /api/skills?full=1 returns complete data."""
    _make_workspace(tmp_path, monkeypatch)
    client = _client()
    r = client.get("/api/skills?full=1")
    assert r.status_code == 200
    data = r.json()
    assert "skills" in data
    assert "repoNodes" in data
    assert "submodules" in data
    assert "relationships" in data


def test_skills_detail(tmp_path, monkeypatch):
    """GET /api/skills/:id returns skill detail."""
    _make_workspace(tmp_path, monkeypatch)
    client = _client()
    r = client.get("/api/skills/my-skill")
    assert r.status_code == 200
    assert r.json()["name"] == "my-skill"


def test_skills_detail_not_found(tmp_path, monkeypatch):
    """GET /api/skills/:id returns 404 for unknown skill."""
    _make_workspace(tmp_path, monkeypatch)
    client = _client()
    r = client.get("/api/skills/nonexistent")
    assert r.status_code == 404


def test_skills_stats(tmp_path, monkeypatch):
    """GET /api/skills/:id/stats returns stats."""
    _make_workspace(tmp_path, monkeypatch)
    client = _client()
    r = client.get("/api/skills/my-skill/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "my-skill"
    assert "fileCount" in data
    assert "type" in data


def test_skills_no_workspace(tmp_path, monkeypatch):
    """Without workspace, skills endpoint returns 400."""
    _use_temp_config(tmp_path, monkeypatch)
    cfg = cfgmod.load_config()
    # workspace_path remains None
    cfgmod.save_config(cfg)

    client = _client()
    r = client.get("/api/skills")
    assert r.status_code == 400


def test_sync_targets(tmp_path, monkeypatch):
    """GET /api/sync/targets returns target list."""
    _use_temp_config(tmp_path, monkeypatch)
    client = _client()
    r = client.get("/api/sync/targets")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_sync_discover_home(tmp_path, monkeypatch):
    """GET /api/sync/discover-home returns agent dirs."""
    client = _client()
    r = client.get("/api/sync/discover-home")
    assert r.status_code == 200
    data = r.json()
    assert "agent_dirs" in data
    assert isinstance(data["agent_dirs"], list)


def test_submodule_refresh_single(tmp_path, monkeypatch):
    """POST /api/submodules/refresh refreshes one submodule when path is provided."""
    _make_workspace(tmp_path, monkeypatch)
    client = _client()

    monkeypatch.setattr(submodules_api, "read_submodule_configs", lambda ws: [
        {"path": "repos/demo", "branch": "main", "description": "Demo"},
    ])
    monkeypatch.setattr(submodules_api, "_run", lambda *args, **kwargs: "")
    monkeypatch.setattr(submodules_api, "get_submodule_status", lambda ws, path, branch: {
        "syncState": "synced",
        "branch": branch,
    })
    monkeypatch.setattr(Path, "is_dir", lambda self: True)

    r = client.post("/api/submodules/refresh", json={"path": "repos/demo"})
    assert r.status_code == 200
    data = r.json()
    assert data["path"] == "repos/demo"
    assert data["status"]["syncState"] == "synced"
    assert data["error"] is None


def test_submodule_refresh_all_without_path(tmp_path, monkeypatch):
    """POST /api/submodules/refresh without path refreshes all submodules."""
    _make_workspace(tmp_path, monkeypatch)
    client = _client()

    configs = [
        {"path": "repos/a", "branch": "main", "description": "A"},
        {"path": "repos/b", "branch": "develop", "description": "B"},
    ]
    monkeypatch.setattr(submodules_api, "read_submodule_configs", lambda ws: configs)
    monkeypatch.setattr(submodules_api, "_run", lambda *args, **kwargs: "")
    monkeypatch.setattr(submodules_api, "get_submodule_status", lambda ws, path, branch: {
        "syncState": "synced",
        "branch": branch,
        "path": path,
    })

    r = client.post("/api/submodules/refresh", json={})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data["checkedAt"], int)
    assert [item["path"] for item in data["results"]] == ["repos/a", "repos/b"]
    assert all(item["error"] is None for item in data["results"])


def test_submodule_sync_pulls_remote_and_stages_parent_pointer(tmp_path, monkeypatch):
    """POST /api/submodules/sync pulls a behind submodule and stages the gitlink."""
    _make_workspace(tmp_path, monkeypatch)
    client = _client()

    subdir = tmp_path / "repos" / "demo"
    subdir.mkdir(parents=True)
    calls = []

    monkeypatch.setattr(submodules_api, "_get_submodule_branch", lambda ws, path: "main")
    monkeypatch.setattr(submodules_api, "_is_head_detached", lambda ws, path: False)
    monkeypatch.setattr(submodules_api, "_get_submodule_index_status", lambda ws, path: {
        "indexAhead": 0,
        "indexBehind": 1,
        "indexDirty": False,
    })
    monkeypatch.setattr(submodules_api, "get_submodule_status", lambda ws, path, branch: {
        "syncState": "synced",
        "branch": branch,
    })

    def fake_run(cmd, cwd, timeout=30):
        calls.append((cmd, cwd, timeout))
        if cmd == "git status --porcelain -- repos/demo":
            return "M  repos/demo"
        if cmd.startswith("git status"):
            return ""
        if cmd.startswith("git rev-list"):
            return "0\t2" if not any(c[0].startswith("git pull") for c in calls) else "0\t0"
        return ""

    monkeypatch.setattr(submodules_api, "_run", fake_run)

    r = client.post("/api/submodules/sync", json={"path": "repos/demo"})

    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["steps"] == [
        "fetch",
        "pull",
        "stage-parent-pointer",
        "commit-parent-pointer",
    ]
    assert data["parentPointerStaged"] is True
    assert data["parentPointerCommitted"] is True
    assert ("git pull --ff-only origin main", str(subdir), 120) in calls
    assert ("git add -- repos/demo", str(tmp_path), 30) in calls
    assert (
        "git commit -m 'dashboard: sync repos/demo submodule' -- repos/demo",
        str(tmp_path),
        30,
    ) in calls


def test_workspace_current_and_switch(tmp_path, monkeypatch):
    """Workspace current/switch endpoints update config pointer."""
    _use_temp_config(tmp_path, monkeypatch)

    first_ws = tmp_path / "first-workspace"
    first_ws.mkdir()
    (first_ws / "skills").mkdir()

    second_ws = tmp_path / "second-workspace"
    second_ws.mkdir()
    (second_ws / "skills").mkdir()

    client = _client()

    current = client.get("/api/workspace/current")
    assert current.status_code == 200
    assert current.json()["workspace_path"] is None

    switched = client.post("/api/workspace/switch", json={"path": str(second_ws)})
    assert switched.status_code == 200
    assert switched.json()["workspace_path"] == str(second_ws.resolve())

    current = client.get("/api/workspace/current")
    assert current.status_code == 200
    assert current.json()["workspace_path"] == str(second_ws.resolve())


def test_registry_register_skill(tmp_path, monkeypatch):
    """POST /api/registry/register imports an external skill into workspace."""
    ws = _make_workspace(tmp_path, monkeypatch)
    source = tmp_path / "external-skill"
    source.mkdir()
    (source / "SKILL.md").write_text(
        "---\nname: external-skill\ndescription: Imported\n---\n\n# external-skill\n",
        encoding="utf-8",
    )
    (source / "tool.sh").write_text("echo hi\n", encoding="utf-8")

    client = _client()
    r = client.post("/api/registry/register", json={
        "sourcePath": str(source),
        "force": False,
    })

    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["data"]["name"] == "external-skill"
    assert data["data"]["skillPath"] == "skills/external-skill"
    assert (ws / "skills" / "external-skill" / "SKILL.md").exists()
    assert (ws / "skills" / "external-skill" / "tool.sh").exists()


def test_registry_register_conflict_returns_409(tmp_path, monkeypatch):
    """POST /api/registry/register returns 409 when skill already exists."""
    _make_workspace(tmp_path, monkeypatch)
    source = tmp_path / "duplicate-source"
    source.mkdir()
    (source / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: Duplicate\n---\n\n# duplicate\n",
        encoding="utf-8",
    )

    client = _client()
    r = client.post("/api/registry/register", json={
        "sourcePath": str(source),
        "force": False,
    })

    assert r.status_code == 409
    data = r.json()
    assert "already exists" in data["detail"]


def test_registry_register_force_overwrites_existing_skill(tmp_path, monkeypatch):
    """POST /api/registry/register with force replaces existing skill files."""
    ws = _make_workspace(tmp_path, monkeypatch)
    source = tmp_path / "replacement-source"
    source.mkdir()
    (source / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: Replacement\n---\n\n# replaced\n",
        encoding="utf-8",
    )
    (source / "new-tool.py").write_text("print('new')\n", encoding="utf-8")

    client = _client()
    r = client.post("/api/registry/register", json={
        "sourcePath": str(source),
        "force": True,
    })

    assert r.status_code == 200
    assert r.json()["success"] is True
    skill_dir = ws / "skills" / "my-skill"
    assert "replaced" in (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert (skill_dir / "new-tool.py").exists()


def test_registry_convert_skill(tmp_path, monkeypatch):
    """POST /api/registry/convert moves a file skill into repos/<name>-cli."""
    ws = _make_workspace(tmp_path, monkeypatch)
    client = _client()

    r = client.post("/api/registry/convert", json={"name": "my-skill"})

    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["data"]["name"] == "my-skill"
    assert data["data"]["repoPath"] == "repos/my-skill-cli"
    assert data["data"]["skillPath"] == "repos/my-skill-cli/skill/my-skill"
    assert not (ws / "skills" / "my-skill").exists()
    assert (ws / "repos" / "my-skill-cli" / "pyproject.toml").exists()
    assert (ws / "repos" / "my-skill-cli" / "skill" / "my-skill" / "SKILL.md").exists()


def test_registry_convert_missing_skill_returns_404(tmp_path, monkeypatch):
    """POST /api/registry/convert returns 404 for unknown skills."""
    _make_workspace(tmp_path, monkeypatch)
    client = _client()

    r = client.post("/api/registry/convert", json={"name": "missing-skill"})

    assert r.status_code == 404
    assert "not found" in r.json()["detail"]
