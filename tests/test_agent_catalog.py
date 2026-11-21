"""Tests for built-in coding agent directory catalog, auto-detection, API, and CLI."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from click.testing import CliRunner
from fastapi.testclient import TestClient

import skillreg.config as cfgmod
from skillreg.cli import cli
from skillreg.server import create_app
from skillreg.services import agent_catalog, sync_files, sync_manager


def _setup_env(tmp_path: Path, monkeypatch, *, skills: list[str] | None = None):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    for var in (
        "CLAUDE_CONFIG_DIR",
        "CODEX_HOME",
        "COPILOT_HOME",
        "OPENCODE_CONFIG_DIR",
        "XDG_CONFIG_HOME",
        "CODEBUDDY_CONFIG_DIR",
        "WORKBUDDY_CONFIG_DIR",
        "PI_CODING_AGENT_DIR",
        "KIMI_CODE_HOME",
        "QWEN_HOME",
        "VIBE_HOME",
        "HERMES_HOME",
        "DSH_HOME",
        "GROK_HOME",
        "MINIMAX_DATA_DIR",
    ):
        monkeypatch.delenv(var, raising=False)

    cfg_path = tmp_path / "config" / "config.json"
    monkeypatch.setattr(cfgmod, "CONFIG_FILE", cfg_path)
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", cfg_path.parent)
    monkeypatch.setattr(sync_manager, "_PROJECTS_DIR", tmp_path / "projects")
    monkeypatch.setattr(
        sync_manager, "_PROJECTS_FILE", tmp_path / "projects" / "projects.json"
    )

    workspace = tmp_path / "workspace"
    (workspace / "skills").mkdir(parents=True)
    (workspace / "repos").mkdir(parents=True)
    for name in skills or []:
        skill_dir = workspace / "skills" / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Demo {name}\n---\n\n# {name}\n",
            encoding="utf-8",
        )

    cfg = cfgmod.load_config()
    cfg.workspace_path = str(workspace)
    cfgmod.save_config(cfg)
    return fake_home, workspace


def test_builtin_catalog_covers_magpie_agents_and_aliases():
    ids = {spec.id for spec in agent_catalog.list_builtin_agents()}
    for expected in (
        "agents",
        "claude",
        "codex",
        "cursor",
        "gemini",
        "antigravity",
        "copilot",
        "opencode",
        "codebuddy",
        "workbuddy",
        "pi",
        "cline",
        "droid",
        "kimi",
        "qwen",
        "qoder",
        "kiro",
        "crush",
        "vibe",
        "hermes",
        "dsh",
        "commandcode",
        "devin",
        "grok",
        "zcode",
        "alma",
        "omp",
        "minimax-code",
    ):
        assert expected in ids

    assert agent_catalog.get_agent_spec("claude-code").id == "claude"
    assert agent_catalog.get_agent_spec("agy").id == "antigravity"
    assert agent_catalog.get_agent_spec("oc").id == "opencode"
    assert agent_catalog.get_agent_spec("factory-droid").id == "droid"
    assert agent_catalog.get_agent_spec("cursor-agent").id == "cursor"
    assert agent_catalog.get_agent_spec("Claude Code").id == "claude"
    # Legacy specs are excluded from default presets but still resolvable.
    assert "tclaude" not in ids
    assert agent_catalog.get_agent_spec("tclaude").legacy is True


def test_detect_home_agents_filters_leftovers_and_empty_scaffolds(tmp_path):
    home = tmp_path / "home"
    home.mkdir()

    # Genuine agent directories with config files
    (home / ".claude").mkdir()
    (home / ".claude" / "settings.json").write_text("{}", encoding="utf-8")
    (home / ".cursor").mkdir()
    (home / ".cursor" / "mcp.json").write_text("{}", encoding="utf-8")
    (home / ".config" / "opencode").mkdir(parents=True)
    (home / ".config" / "opencode" / "opencode.json").write_text("{}", encoding="utf-8")
    (home / ".gemini" / "config").mkdir(parents=True)
    (home / ".gemini" / "config" / "mcp_config.json").write_text("{}", encoding="utf-8")
    (home / ".agents" / "skills").mkdir(parents=True)

    # Leftover-only runtime dirs should NOT be detected
    (home / ".codebuddy" / "logs").mkdir(parents=True)
    (home / ".codebuddy" / "diagnostics").mkdir(parents=True)
    (home / ".codebuddy" / "logs" / "a.log").write_text("x", encoding="utf-8")
    (home / ".qwen" / "debug").mkdir(parents=True)
    (home / ".hermes" / "cache").mkdir(parents=True)

    # Empty skills/ scaffold without config or binary should NOT be detected
    (home / ".cline" / "skills").mkdir(parents=True)
    (home / ".cline" / ".DS_Store").write_text("", encoding="utf-8")

    # Non-empty skills/ directory SHOULD be detected
    (home / ".factory" / "skills" / "my-skill").mkdir(parents=True)
    (home / ".factory" / "skills" / "my-skill" / "SKILL.md").write_text("# s\n", encoding="utf-8")

    # Path taken by a regular file should NOT be detected even with binary present
    (home / ".dsh").write_text("not a dir", encoding="utf-8")

    detected = agent_catalog.detect_home_agents(
        home=home,
        env={},
        which=lambda b: "/usr/bin/" + b if b in {"codex", "dsh"} else None,
        include_undetected=False,
    )
    by_id = {item["id"]: item for item in detected}

    assert set(by_id) == {
        "agents",
        "claude",
        "codex",
        "cursor",
        "gemini",
        "antigravity",
        "opencode",
        "droid",
    }
    assert by_id["agents"]["shared"] is True
    assert by_id["agents"]["detectedBy"] == "skills"
    assert by_id["claude"]["detectedBy"] == "directory"
    assert by_id["codex"]["detectedBy"] == "binary"
    assert by_id["codex"]["detectedBinary"] == "codex"
    assert by_id["droid"]["detectedBy"] == "skills"
    assert by_id["opencode"]["rel_path"] == ".config/opencode/skills"
    assert by_id["antigravity"]["rel_path"] == ".gemini/config/skills"
    assert "codebuddy" not in by_id
    assert "qwen" not in by_id
    assert "hermes" not in by_id
    assert "cline" not in by_id
    assert "dsh" not in by_id


def test_detect_home_agents_honors_absolute_env_overrides_and_kimi_legacy(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    custom_claude = tmp_path / "custom-claude"
    custom_claude.mkdir()
    (custom_claude / "settings.json").write_text("{}", encoding="utf-8")
    xdg_config = tmp_path / "xdg"
    (xdg_config / "opencode").mkdir(parents=True)
    (xdg_config / "opencode" / "opencode.json").write_text("{}", encoding="utf-8")
    (home / ".kimi").mkdir()
    (home / ".kimi" / "config.toml").write_text("", encoding="utf-8")

    detected = agent_catalog.detect_home_agents(
        home=home,
        env={
            "CLAUDE_CONFIG_DIR": str(custom_claude),
            "CODEX_HOME": "relative/ignored",
            "XDG_CONFIG_HOME": str(xdg_config),
        },
        which=lambda _b: None,
    )
    by_id = {item["id"]: item for item in detected}

    assert by_id["claude"]["path"] == str(custom_claude / "skills")
    assert by_id["opencode"]["path"] == str(xdg_config / "opencode" / "skills")
    assert by_id["kimi"]["path"] == str(home / ".kimi" / "skills")
    assert "codex" not in by_id


def test_discover_project_agent_dirs_covers_common_coding_agents(tmp_path):
    project = tmp_path / "app"
    project.mkdir()
    for rel in (".claude", ".agents/skills", ".cursor", ".opencode", ".qoder", ".factory"):
        (project / rel).mkdir(parents=True)
    # Leftover-only project folder is ignored
    (project / ".qwen" / "debug").mkdir(parents=True)

    found = agent_catalog.discover_project_agent_dirs(project)
    by_agent = {item["agent"]: item for item in found}

    assert set(by_agent) == {"agents", "claude", "cursor", "opencode", "qoder", "droid"}
    assert by_agent["cursor"]["path"] == str(project / ".cursor" / "skills")
    assert by_agent["droid"]["path"] == str(project / ".factory" / "skills")
    assert by_agent["agents"]["exists"] is True


def test_zero_config_builtin_targets_work_via_api_and_preserve_manual_targets(
    tmp_path, monkeypatch
):
    home, _workspace = _setup_env(tmp_path, monkeypatch, skills=["demo-skill"])
    (home / ".claude").mkdir()
    (home / ".claude" / "settings.json").write_text("{}", encoding="utf-8")
    (home / ".cursor").mkdir()
    (home / ".cursor" / "mcp.json").write_text("{}", encoding="utf-8")

    client = TestClient(create_app())

    # Without any manually configured targets, built-ins appear immediately.
    cfg_resp = client.get("/api/sync/config")
    assert cfg_resp.status_code == 200
    targets = cfg_resp.json()["targets"]
    assert [t["agentKind"] for t in targets] == ["claude", "cursor"]
    assert all(t["builtin"] is True for t in targets)

    # Installing directly to a built-in target works with zero manual setup.
    exec_resp = client.post(
        "/api/sync/execute",
        json={"target": "Claude Code", "skills": ["demo-skill"]},
    )
    assert exec_resp.status_code == 200, exec_resp.text
    assert exec_resp.json()["success"] is True
    assert (home / ".claude" / "skills" / "demo-skill" / "SKILL.md").is_file()

    # Sync status reflects the installed built-in target.
    status_resp = client.get("/api/sync/status", params={"skill": "demo-skill"})
    assert status_resp.status_code == 200
    status_by_target = {row["target"]: row["status"] for row in status_resp.json()}
    assert status_by_target[str(home / ".claude" / "skills")] == "synced"
    assert status_by_target[str(home / ".cursor" / "skills")] == "missing"

    # Manual custom targets remain fully supported and appear first without persisting built-ins.
    custom_dir = tmp_path / "my-custom-skills"
    add_resp = client.post(
        "/api/sync/targets",
        json={"name": "custom-lab", "path": str(custom_dir)},
    )
    assert add_resp.status_code == 200
    assert add_resp.json()["target"]["builtin"] is False

    raw_cfg = cfgmod.load_config()
    assert len(raw_cfg.targets) == 1
    assert raw_cfg.targets[0]["name"] == "custom-lab"

    updated_targets = client.get("/api/sync/config").json()["targets"]
    assert updated_targets[0]["name"] == "custom-lab"
    assert updated_targets[0]["builtin"] is False
    assert [t["agentKind"] for t in updated_targets[1:]] == ["claude", "cursor"]

    # Promoting a built-in path as a custom target deduplicates cleanly.
    promote_resp = client.post(
        "/api/sync/targets",
        json={"name": "work-claude", "path": str(home / ".claude" / "skills")},
    )
    assert promote_resp.status_code == 200
    deduped = client.get("/api/sync/config").json()["targets"]
    claude_entries = [t for t in deduped if t["path"] == str(home / ".claude" / "skills")]
    assert len(claude_entries) == 1
    assert claude_entries[0]["name"] == "work-claude"
    assert claude_entries[0]["builtin"] is False

    # Built-in agents can be hidden and re-enabled cleanly.
    hide_resp = client.put("/api/sync/agents/cursor", json={"enabled": False})
    assert hide_resp.status_code == 200
    assert all(
        t["agentKind"] != "cursor"
        for t in client.get("/api/sync/config").json()["targets"]
    )
    catalog_resp = client.get("/api/sync/agents", params={"include_undetected": "true"})
    assert catalog_resp.status_code == 200
    catalog = catalog_resp.json()
    assert catalog["detectedCount"] == 2
    cursor_entry = next(a for a in catalog["agents"] if a["id"] == "cursor")
    assert cursor_entry["detected"] is True
    assert cursor_entry["enabled"] is False
    assert cursor_entry["active"] is False
    assert any(a["id"] == "opencode" and a["detected"] is False for a in catalog["agents"])

    show_resp = client.put("/api/sync/agents/cursor", json={"enabled": True})
    assert show_resp.status_code == 200
    assert any(
        t["agentKind"] == "cursor"
        for t in client.get("/api/sync/config").json()["targets"]
    )

    # Renaming a built-in target's path is rejected cleanly.
    rename_resp = client.put(
        f"/api/sync/targets/{home / '.cursor' / 'skills'}/rename",
        json={"newName": str(tmp_path / "elsewhere")},
    )
    assert rename_resp.status_code == 400


def test_cli_target_list_discover_and_zero_config_sync(tmp_path, monkeypatch):
    home, _workspace = _setup_env(tmp_path, monkeypatch, skills=["alpha"])
    (home / ".cursor").mkdir()
    (home / ".cursor" / "mcp.json").write_text("{}", encoding="utf-8")
    (home / ".config" / "opencode").mkdir(parents=True)
    (home / ".config" / "opencode" / "opencode.json").write_text("{}", encoding="utf-8")

    runner = CliRunner()

    listed = runner.invoke(cli, ["target", "list", "--json"])
    assert listed.exit_code == 0, listed.output
    records = json.loads(listed.output)
    assert [r["agentKind"] for r in records] == ["cursor", "opencode"]
    assert all(r["builtin"] is True for r in records)

    discovered = runner.invoke(cli, ["target", "discover"])
    assert discovered.exit_code == 0, discovered.output
    payload = json.loads(discovered.output)
    assert payload["detectedCount"] == 2
    assert {a["id"] for a in payload["agents"]} == {"cursor", "opencode"}

    discovered_all = runner.invoke(cli, ["target", "discover", "--all"])
    assert discovered_all.exit_code == 0, discovered_all.output
    payload_all = json.loads(discovered_all.output)
    assert payload_all["totalCount"] > payload_all["detectedCount"]

    synced = runner.invoke(cli, ["sync", "execute", "--target", "opencode"])
    assert synced.exit_code == 0, synced.output
    assert (home / ".config" / "opencode" / "skills" / "alpha" / "SKILL.md").is_file()


def test_sync_files_worker_discover_matches_nested_and_project_agents_py36(
    tmp_path, monkeypatch
):
    home, _workspace = _setup_env(tmp_path, monkeypatch)
    (home / ".config" / "opencode").mkdir(parents=True)
    (home / ".config" / "opencode" / "opencode.json").write_text("{}", encoding="utf-8")
    (home / ".gemini" / "config").mkdir(parents=True)
    (home / ".gemini" / "config" / "mcp_config.json").write_text("{}", encoding="utf-8")
    (home / ".pi" / "agent").mkdir(parents=True)
    (home / ".pi" / "agent" / "settings.json").write_text("{}", encoding="utf-8")
    (home / ".qwen" / "debug").mkdir(parents=True)

    discovered = sync_files.dispatch({"operation": "discover"})
    by_kind = {item["agentKind"]: item for item in discovered["targets"]}
    assert set(by_kind) == {"opencode", "gemini", "antigravity", "pi"}
    assert by_kind["opencode"]["path"] == str(home / ".config" / "opencode" / "skills")
    assert by_kind["antigravity"]["path"] == str(home / ".gemini" / "config" / "skills")
    assert by_kind["pi"]["path"] == str(home / ".pi" / "agent" / "skills")
    assert "qwen" not in by_kind

    project = tmp_path / "repo"
    (project / ".codex").mkdir(parents=True)
    (project / ".cursor").mkdir(parents=True)
    proj_discovered = sync_files.dispatch({"operation": "discover", "root": str(project)})
    assert {item["agentKind"] for item in proj_discovered["targets"]} == {"codex", "cursor"}

    # Maintain strict Python 3.6 syntax compatibility for SSH worker upload.
    ast.parse(Path(sync_files.__file__).read_text(encoding="utf-8"), feature_version=(3, 6))
