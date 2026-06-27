"""Tests for skills and sync API endpoints."""

from __future__ import annotations

import skillreg.config as cfgmod
from skillreg.server import create_app


def _client():
    from fastapi.testclient import TestClient
    return TestClient(create_app())


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

    cfg_path = tmp_path / "config.json"
    monkeypatch.setattr(cfgmod, "CONFIG_FILE", cfg_path)
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", cfg_path.parent)
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
    cfg_path = tmp_path / "config.json"
    monkeypatch.setattr(cfgmod, "CONFIG_FILE", cfg_path)
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", cfg_path.parent)
    cfg = cfgmod.load_config()
    # workspace_path remains None
    cfgmod.save_config(cfg)

    client = _client()
    r = client.get("/api/skills")
    assert r.status_code == 400


def test_sync_targets(tmp_path, monkeypatch):
    """GET /api/sync/targets returns target list."""
    cfg_path = tmp_path / "config.json"
    monkeypatch.setattr(cfgmod, "CONFIG_FILE", cfg_path)
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", cfg_path.parent)
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
