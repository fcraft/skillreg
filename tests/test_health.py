"""Tests for the /api/health endpoint."""

from __future__ import annotations

import skillreg.config as cfgmod
from skillreg.server import app


def _client():
    from fastapi.testclient import TestClient

    return TestClient(app)


def test_health_no_workspace(tmp_path, monkeypatch):
    """With an unconfigured workspace, health returns null + message."""
    cfg_path = tmp_path / "config.json"
    monkeypatch.setattr(cfgmod, "CONFIG_FILE", cfg_path)
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", cfg_path.parent)

    # Avoid accidentally picking up the dev dashboard mount path resolution
    # is fine; /api/health is registered before the static catch-all mount.
    client = _client()
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["workspace_path"] is None
    assert "message" in data and "workspace" in data["message"]


def test_health_with_workspace(tmp_path, monkeypatch):
    """With a configured workspace_path, health returns it and no message."""
    cfg_path = tmp_path / "config.json"
    monkeypatch.setattr(cfgmod, "CONFIG_FILE", cfg_path)
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", cfg_path.parent)

    cfg = cfgmod.load_config()
    cfg.workspace_path = str(tmp_path / "my-workspace")
    cfgmod.save_config(cfg)

    client = _client()
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["workspace_path"] == str(tmp_path / "my-workspace")
    assert "message" not in data
