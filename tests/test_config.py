"""Tests for ~/.skillreg/config.json creation and read/write round-trip."""

from __future__ import annotations

import json

from click.testing import CliRunner

import skillreg.cli as climod
import skillreg.config as cfgmod
from skillreg.cli import cli
from skillreg.config import SkillregConfig


def test_creates_config_when_missing(tmp_path, monkeypatch):
    """First load on a missing config file creates it with all expected fields."""
    cfg_path = tmp_path / "config.json"
    monkeypatch.setattr(cfgmod, "CONFIG_FILE", cfg_path)
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", cfg_path.parent)

    cfg = cfgmod.load_config()

    # File was created on disk with the default structure.
    assert cfg_path.exists()
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert set(data.keys()) >= {"workspace_path", "targets", "target_skill_filters", "agents"}
    assert data["workspace_path"] is None
    assert data["targets"] == []
    assert data["target_skill_filters"] == {}
    assert data["agents"] == {}

    # Returned model matches.
    assert isinstance(cfg, SkillregConfig)
    assert cfg.workspace_path is None
    assert cfg.targets == []
    assert cfg.agents == {}


def test_roundtrip_preserves_fields(tmp_path, monkeypatch):
    """save -> load preserves workspace_path, targets, agents."""
    cfg_path = tmp_path / "config.json"
    monkeypatch.setattr(cfgmod, "CONFIG_FILE", cfg_path)
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", cfg_path.parent)

    cfg = cfgmod.load_config()
    cfg.workspace_path = str(tmp_path / "ws")
    cfg.targets = ["~/.claude/skills", "~/.codebuddy/skills"]
    cfg.target_skill_filters = {"~/.claude/skills": ["demo-skill"]}
    cfg.agents = {
        "claude": {"skill_dir": "~/.claude/skills"},
        "codex": {"skill_dir": "~/.codex/skills"},
    }
    cfgmod.save_config(cfg)

    cfg2 = cfgmod.load_config()
    assert cfg2.workspace_path == str(tmp_path / "ws")
    assert cfg2.targets == ["~/.claude/skills", "~/.codebuddy/skills"]
    assert cfg2.target_skill_filters == {"~/.claude/skills": ["demo-skill"]}
    assert cfg2.agents["claude"]["skill_dir"] == "~/.claude/skills"
    assert cfg2.agents["codex"]["skill_dir"] == "~/.codex/skills"


def test_load_existing_partial_config_defaults_missing_keys(tmp_path, monkeypatch):
    """An existing config missing some keys is still loaded (defaults applied)."""
    cfg_path = tmp_path / "config.json"
    monkeypatch.setattr(cfgmod, "CONFIG_FILE", cfg_path)
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", cfg_path.parent)

    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(
        json.dumps({"workspace_path": "/some/workspace"}), encoding="utf-8"
    )

    cfg = cfgmod.load_config()
    assert cfg.workspace_path == "/some/workspace"
    assert cfg.targets == []
    assert cfg.target_skill_filters == {}
    assert cfg.agents == {}


def test_workspace_create_prints_current_workspace_context(tmp_path, monkeypatch):
    """Workspace-affecting commands print enough context for agents to continue."""
    cfg_path = tmp_path / "config.json"
    ws = tmp_path / "workspace"
    monkeypatch.setattr(cfgmod, "CONFIG_FILE", cfg_path)
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", cfg_path.parent)
    monkeypatch.setattr(climod, "CONFIG_FILE", cfg_path)

    result = CliRunner().invoke(cli, ["workspace", "create", str(ws)])

    assert result.exit_code == 0
    assert f"已创建 workspace: {ws}" in result.output
    assert "创建 workspace 后的 skillreg 上下文" in result.output
    assert f"当前 workspace : {ws}" in result.output
