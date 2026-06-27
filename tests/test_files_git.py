"""Tests for files and git API routes."""

from __future__ import annotations

import skillreg.config as cfgmod
from skillreg.server import create_app


def _client():
    from fastapi.testclient import TestClient
    return TestClient(create_app())


def _setup_workspace(tmp_path, monkeypatch, with_git=False):
    """Create a workspace with a test file."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "skills").mkdir()
    (ws / "repos").mkdir()
    (ws / "README.md").write_text("# Test Workspace\n", encoding="utf-8")
    (ws / "src").mkdir()
    (ws / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")

    if with_git:
        import subprocess
        subprocess.run(
            ["git", "init"], cwd=str(ws), capture_output=True, text=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=str(ws), capture_output=True, text=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=str(ws), capture_output=True, text=True,
        )
        subprocess.run(
            ["git", "add", "-A"], cwd=str(ws), capture_output=True, text=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=str(ws), capture_output=True, text=True,
        )

    cfg_path = tmp_path / "config.json"
    monkeypatch.setattr(cfgmod, "CONFIG_FILE", cfg_path)
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", cfg_path.parent)
    cfg = cfgmod.load_config(cfg_path)
    cfg.workspace_path = str(ws)
    cfgmod.save_config(cfg, cfg_path)
    return ws


class TestFiles:
    def test_file_tree(self, tmp_path, monkeypatch):
        _setup_workspace(tmp_path, monkeypatch)
        client = _client()
        r = client.get("/api/files/tree")
        assert r.status_code == 200
        data = r.json()
        assert data["type"] == "dir"
        assert data["name"] == "."
        children_names = [c["name"] for c in data.get("children", [])]
        assert "README.md" in children_names
        assert "src" in children_names

    def test_file_content(self, tmp_path, monkeypatch):
        ws = _setup_workspace(tmp_path, monkeypatch)
        client = _client()
        r = client.get("/api/files/content?root=.&path=README.md")
        assert r.status_code == 200
        data = r.json()
        assert "content" in data
        assert "# Test Workspace" in data["content"]

    def test_file_content_large(self, tmp_path, monkeypatch):
        ws = _setup_workspace(tmp_path, monkeypatch)
        # Create a file larger than 100KB
        big_file = ws / "big.txt"
        big_file.write_text("x" * 200_000, encoding="utf-8")

        client = _client()
        r = client.get("/api/files/content?root=.&path=big.txt")
        assert r.status_code == 413


class TestGit:
    def test_git_logs(self, tmp_path, monkeypatch):
        _setup_workspace(tmp_path, monkeypatch, with_git=True)
        client = _client()
        r = client.get("/api/git/logs")
        assert r.status_code == 200
        data = r.json()
        assert "main" in data
        assert len(data["main"]) >= 1
        assert "hash" in data["main"][0]
        assert "message" in data["main"][0]
