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


def test_discovered_agents_join_by_choice_and_preserve_manual_targets(
    tmp_path, monkeypatch
):
    home, _workspace = _setup_env(tmp_path, monkeypatch, skills=["demo-skill"])
    (home / ".claude").mkdir()
    (home / ".claude" / "settings.json").write_text("{}", encoding="utf-8")
    (home / ".cursor").mkdir()
    (home / ".cursor" / "mcp.json").write_text("{}", encoding="utf-8")

    client = TestClient(create_app())

    assert client.get("/api/sync/config").json()["targets"] == []
    candidates = client.get("/api/sync/agents").json()
    assert candidates["onboarding"] == "pending"
    assert len(candidates["agents"]) == 31
    assert not any(agent["added"] for agent in candidates["agents"])
    invalid = client.post("/api/sync/agents/join", json={"agentIds": ["cursor", "unknown"]})
    assert invalid.status_code == 404
    assert client.get("/api/sync/config").json()["targets"] == []
    joined = client.post("/api/sync/agents/join", json={
        "agentIds": ["claude", "cursor"], "onboarding": "completed",
    })
    assert joined.status_code == 200
    assert cfgmod.load_config().agent_onboarding == "completed"
    cfg_resp = client.get("/api/sync/config")
    targets = cfg_resp.json()["targets"]
    assert [t["agentKind"] for t in targets] == ["claude", "cursor"]
    assert all(t["builtin"] is True for t in targets)

    # Joined targets support installation by display name.
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

    assert client.delete("/api/sync/targets/work-claude").status_code == 200
    candidate = next(a for a in client.get("/api/sync/agents").json()["agents"] if a["id"] == "claude")
    assert candidate["detected"] and not candidate["added"]
    assert (home / ".claude/skills/demo-skill/SKILL.md").is_file()

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


def test_cli_discover_then_add_and_sync(tmp_path, monkeypatch):
    home, _workspace = _setup_env(tmp_path, monkeypatch, skills=["alpha"])
    (home / ".cursor").mkdir()
    (home / ".cursor" / "mcp.json").write_text("{}", encoding="utf-8")
    (home / ".config" / "opencode").mkdir(parents=True)
    (home / ".config" / "opencode" / "opencode.json").write_text("{}", encoding="utf-8")

    runner = CliRunner()

    listed = runner.invoke(cli, ["target", "list", "--json"])
    assert listed.exit_code == 0, listed.output
    records = json.loads(listed.output)
    assert records == []

    discovered = runner.invoke(cli, ["target", "discover"])
    assert discovered.exit_code == 0, discovered.output
    payload = json.loads(discovered.output)
    assert payload["detectedCount"] == 2
    assert {a["id"] for a in payload["agents"]} == {"cursor", "opencode"}

    discovered_all = runner.invoke(cli, ["target", "discover", "--all"])
    assert discovered_all.exit_code == 0, discovered_all.output
    payload_all = json.loads(discovered_all.output)
    assert payload_all["totalCount"] > payload_all["detectedCount"]

    added = runner.invoke(cli, ["target", "add", str(home / ".config/opencode/skills")])
    assert added.exit_code == 0, added.output
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


def test_builtin_catalog_icons_cover_all_agents_and_match_assets():
    all_specs = agent_catalog.list_builtin_agents(include_legacy=True)
    assert len(all_specs) == 31

    icons_dir = (
        Path(__file__).resolve().parents[1]
        / "dashboard"
        / "src"
        / "assets"
        / "provider-icons"
    )
    assert (icons_dir / "custom.svg").is_file()
    assert (icons_dir / "ATTRIBUTION.md").is_file()

    for spec in all_specs:
        assert spec.icon, f"Missing icon on AgentSpec {spec.id}"
        assert spec.icon == spec.icon.strip().lower()
        assert (icons_dir / f"{spec.icon}.svg").is_file(), (
            f"Missing localized SVG for {spec.id} ({spec.icon}.svg)"
        )

    # sync_files.AGENT_ICONS (Py3.6 SSH worker) must match agent_catalog 1:1.
    expected_map = {spec.id: spec.icon for spec in all_specs}
    assert sync_files.AGENT_ICONS == expected_map
    assert sync_files.DEFAULT_ICON == agent_catalog.DEFAULT_CUSTOM_ICON

    # Aliases, legacy specs, remote paths, and unknown fallbacks resolve accurately.
    assert agent_catalog.icon_for_agent("shared-agents") == "agents"
    assert agent_catalog.icon_for_agent("claude-code") == "claude"
    assert agent_catalog.icon_for_agent("tclaude") == "claude"
    assert agent_catalog.icon_for_agent("tcodex") == "codex"
    assert agent_catalog.icon_for_agent("agent") == "agent"
    assert agent_catalog.icon_for_agent("factory-droid") == "droid"
    assert agent_catalog.icon_for_agent("unknown-custom") == "custom"
    assert agent_catalog.icon_for_agent(None) == "custom"

    assert agent_catalog.icon_for_path("~/.gemini/config/skills", remote=True) == "antigravity"
    assert agent_catalog.icon_for_path("~/.gemini/skills", remote=True) == "gemini"
    assert agent_catalog.icon_for_path("/srv/repo/.opencode/skills", remote=True) == "opencode"
    assert agent_catalog.icon_for_path("/opt/custom/skills", remote=True) == "custom"


def test_sync_apis_serialize_provider_icons_for_builtin_custom_and_project_targets(
    tmp_path, monkeypatch
):
    home, _workspace = _setup_env(tmp_path, monkeypatch, skills=["demo-skill"])
    (home / ".agents" / "skills").mkdir(parents=True)
    (home / ".claude").mkdir()
    (home / ".claude" / "settings.json").write_text("{}", encoding="utf-8")
    (home / ".gemini" / "config").mkdir(parents=True)
    (home / ".gemini" / "config" / "mcp_config.json").write_text("{}", encoding="utf-8")
    (home / ".codebuddy").mkdir()
    (home / ".codebuddy" / "settings.json").write_text("{}", encoding="utf-8")
    (home / ".workbuddy").mkdir()
    (home / ".workbuddy" / "settings.json").write_text("{}", encoding="utf-8")

    custom_dir = tmp_path / "arbitrary-skills"
    custom_dir.mkdir()

    project_dir = tmp_path / "sample-project"
    (project_dir / ".claude").mkdir(parents=True)
    (project_dir / ".cursor").mkdir(parents=True)

    client = TestClient(create_app())

    add_resp = client.post(
        "/api/sync/targets",
        json={"name": "Custom Local", "path": str(custom_dir)},
    )
    assert add_resp.status_code == 200
    assert add_resp.json()["target"]["icon"] == "custom"

    response = client.post("/api/sync/agents/join", json={
        "agentIds": ["agents", "claude", "antigravity", "codebuddy", "workbuddy"],
    })
    assert response.status_code == 200
    # /api/sync/config and /api/sync/targets serialize icons for both custom and built-in targets.
    for endpoint in ("/api/sync/config", "/api/sync/targets", "/api/targets"):
        resp = client.get(endpoint)
        assert resp.status_code == 200
        payload = resp.json()
        items = payload["targets"] if isinstance(payload, dict) else payload
        by_name = {t["name"]: t for t in items}
        assert by_name["Custom Local"]["icon"] == "custom"
        assert by_name["Shared Agents"]["icon"] == "agents"
        assert by_name["Claude Code"]["icon"] == "claude"
        assert by_name["Antigravity"]["icon"] == "antigravity"
        assert by_name["CodeBuddy"]["icon"] == "codebuddy"
        assert by_name["WorkBuddy"]["icon"] == "workbuddy"

    # /api/sync/agents returns icon for every mainstream + legacy built-in provider.
    agents_resp = client.get(
        "/api/sync/agents",
        params={"include_undetected": "true", "include_legacy": "true"},
    )
    assert agents_resp.status_code == 200
    agents = agents_resp.json()["agents"]
    assert len(agents) == 31
    assert all(a.get("icon") for a in agents)
    agents_by_id = {a["id"]: a for a in agents}
    assert agents_by_id["tclaude"]["icon"] == "claude"
    assert agents_by_id["tcodex"]["icon"] == "codex"
    assert agents_by_id["agent"]["icon"] == "agent"

    # /api/sync/discover-home returns icon on every entry.
    home_resp = client.get("/api/sync/discover-home", params={"include_undetected": "true"})
    assert home_resp.status_code == 200
    assert len(home_resp.json()["agent_dirs"]) == 28
    assert all(d.get("icon") for d in home_resp.json()["agent_dirs"])

    # /api/sync/discover returns icon on discovered project agent directories.
    proj_resp = client.get("/api/sync/discover", params={"path": str(project_dir)})
    assert proj_resp.status_code == 200
    proj_dirs = {d["agent"]: d for d in proj_resp.json()["agent_dirs"]}
    assert proj_dirs["claude"]["icon"] == "claude"
    assert proj_dirs["cursor"]["icon"] == "cursor"

    # Project sync status rows expose _icon alongside _agent.
    sync_manager.create_project("DemoProj", [str(project_dir)])
    status_resp = client.get("/api/sync/status", params={"include_projects": "true"})
    assert status_resp.status_code == 200
    project_rows = [r for r in status_resp.json() if r.get("_project") == "DemoProj"]
    assert {r.get("_icon") for r in project_rows} == {"claude", "cursor"}

    # SSH worker discover_targets also emits icon field.
    worker_home = sync_files.dispatch({"operation": "discover"})
    worker_by_kind = {t["agentKind"]: t for t in worker_home["targets"]}
    assert worker_by_kind["antigravity"]["icon"] == "antigravity"
    assert worker_by_kind["codebuddy"]["icon"] == "codebuddy"
    assert worker_by_kind["workbuddy"]["icon"] == "workbuddy"

    worker_proj = sync_files.dispatch({"operation": "discover", "root": str(project_dir)})
    assert {t["icon"] for t in worker_proj["targets"]} == {"claude", "cursor"}


def test_legacy_membership_and_skipped_onboarding(tmp_path, monkeypatch):
    home, _ = _setup_env(tmp_path, monkeypatch)
    cfgmod.CONFIG_FILE.write_text(json.dumps({
        "targets": ["~/.cursor/skills"],
        "agents": {"codex": {"enabled": True}, "claude": {"enabled": False}},
    }))
    client = TestClient(create_app())
    assert {row["agentKind"] for row in client.get("/api/sync/targets").json()} == {"codex", "cursor"}
    assert client.post("/api/sync/agents/join", json={"agentIds": [], "onboarding": "skipped"}).is_success
    assert TestClient(create_app()).get("/api/sync/agents").json()["onboarding"] == "skipped"
    assert client.delete("/api/sync/targets/codex").is_success
    assert not (home / ".codex").exists()
