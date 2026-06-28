"""Tests for the public skillreg CLI command surface."""

from __future__ import annotations

from click.testing import CliRunner

import skillreg.config as cfgmod
import skillreg.services.sync_manager as sync_manager
from skillreg.cli import cli


def _configure(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.json"
    monkeypatch.setattr(cfgmod, "CONFIG_FILE", cfg_path)
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", cfg_path.parent)
    monkeypatch.setattr(sync_manager, "_PROJECTS_DIR", tmp_path / "projects")
    monkeypatch.setattr(sync_manager, "_PROJECTS_FILE", tmp_path / "projects" / "projects.json")

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "skills").mkdir()
    (workspace / "repos").mkdir()

    cfg = cfgmod.load_config()
    cfg.workspace_path = str(workspace)
    cfgmod.save_config(cfg)
    return workspace


def _make_source(tmp_path, name="demo-skill", body="# Demo\n"):
    source = tmp_path / f"source-{name}"
    source.mkdir()
    (source / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Demo\n---\n\n{body}",
        encoding="utf-8",
    )
    (source / "notes.md").write_text("hello\n", encoding="utf-8")
    return source


def test_register_list_convert_and_diff(tmp_path, monkeypatch):
    workspace = _configure(tmp_path, monkeypatch)
    source = _make_source(tmp_path)
    target = tmp_path / "target-skills"
    runner = CliRunner()

    registered = runner.invoke(cli, ["register", str(source)])

    assert registered.exit_code == 0, registered.output
    assert "Registered skill: demo-skill" in registered.output
    assert "skillreg context after register" in registered.output
    assert (workspace / "skills" / "demo-skill" / "SKILL.md").exists()

    listed = runner.invoke(cli, ["list"])

    assert listed.exit_code == 0, listed.output
    assert "demo-skill" in listed.output
    assert "Total: 1 skill(s)" in listed.output

    synced = runner.invoke(cli, ["sync", "execute", "--target", str(target)])

    assert synced.exit_code == 0, synced.output
    assert "Synced 1 skill(s)" in synced.output
    assert (target / "demo-skill" / "SKILL.md").exists()

    (target / "demo-skill" / "notes.md").write_text("changed\n", encoding="utf-8")
    diffed = runner.invoke(cli, ["diff", "demo-skill", "--target", str(target)])

    assert diffed.exit_code == 0, diffed.output
    assert "modified" in diffed.output
    assert "notes.md" in diffed.output

    converted = runner.invoke(cli, ["convert", "demo-skill"])

    assert converted.exit_code == 0, converted.output
    assert "Converted skill: demo-skill" in converted.output
    assert (workspace / "repos" / "demo-skill-cli" / "skill" / "demo-skill" / "SKILL.md").exists()


def test_target_and_sync_status_commands(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    source = _make_source(tmp_path, "status-skill")
    target = tmp_path / "agent" / "skills"
    runner = CliRunner()

    assert runner.invoke(cli, ["register", str(source)]).exit_code == 0

    added = runner.invoke(cli, ["target", "add", str(target), "--name", "codex"])
    assert added.exit_code == 0, added.output
    assert "Added target: codex" in added.output

    targets = runner.invoke(cli, ["target", "list"])
    assert targets.exit_code == 0, targets.output
    assert str(target) in targets.output

    status = runner.invoke(cli, ["sync", "status"])
    assert status.exit_code == 0, status.output
    assert "status-skill" in status.output
    assert "missing" in status.output

    preview = runner.invoke(cli, ["sync", "execute", "--target", str(target), "--dry-run"])
    assert preview.exit_code == 0, preview.output
    assert "Would sync status-skill" in preview.output

    removed = runner.invoke(cli, ["target", "remove", str(target)])
    assert removed.exit_code == 0, removed.output
    assert "Removed target" in removed.output


def test_project_commands_and_project_sync(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    source = _make_source(tmp_path, "project-skill")
    target = tmp_path / "project-target"
    runner = CliRunner()

    assert runner.invoke(cli, ["register", str(source)]).exit_code == 0

    created = runner.invoke(
        cli,
        ["project", "create", "--name", "demo-project", "--target", str(target)],
    )
    assert created.exit_code == 0, created.output
    assert "Created project: demo-project" in created.output

    listed = runner.invoke(cli, ["project", "list"])
    assert listed.exit_code == 0, listed.output
    assert "demo-project" in listed.output

    synced = runner.invoke(cli, ["sync", "execute", "--project", "demo-project"])
    assert synced.exit_code == 0, synced.output
    assert "Synced project: demo-project" in synced.output
    assert (target / "project-skill" / "SKILL.md").exists()

    deleted = runner.invoke(cli, ["project", "delete", "demo-project"])
    assert deleted.exit_code == 0, deleted.output
    assert "Deleted project: demo-project" in deleted.output


def test_workspace_switch_and_current(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    other = tmp_path / "other-workspace"
    other.mkdir()
    (other / "skills").mkdir()
    runner = CliRunner()

    switched = runner.invoke(cli, ["workspace", "switch", str(other)])

    assert switched.exit_code == 0, switched.output
    assert f"Workspace switched to {other}" in switched.output

    current = runner.invoke(cli, ["workspace", "current"])

    assert current.exit_code == 0, current.output
    assert f"current workspace : {other}" in current.output


def test_submodule_list_without_submodules(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)

    result = CliRunner().invoke(cli, ["submodule", "list"])

    assert result.exit_code == 0, result.output
    assert "(no submodules found)" in result.output


def test_dashboard_lifecycle_commands_are_exposed(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    pid_file = tmp_path / "dashboard.pid"
    log_file = tmp_path / "dashboard.log"

    import skillreg.cli as climod

    monkeypatch.setattr(climod, "DASHBOARD_PID_FILE", pid_file)
    monkeypatch.setattr(climod, "DASHBOARD_LOG_FILE", log_file)

    class FakeProc:
        pid = 12345

    monkeypatch.setattr(climod.subprocess, "Popen", lambda *args, **kwargs: FakeProc())
    seen_kills = []

    def fake_kill(pid, sig):
        seen_kills.append((pid, sig))

    monkeypatch.setattr(climod.os, "kill", fake_kill)

    runner = CliRunner()
    started = runner.invoke(cli, ["dashboard", "start", "--port", "9999"])
    assert started.exit_code == 0, started.output
    assert "Dashboard started" in started.output
    assert pid_file.read_text(encoding="utf-8") == "12345"

    status = runner.invoke(cli, ["dashboard", "status"])
    assert status.exit_code == 0, status.output
    assert "Dashboard running" in status.output

    stopped = runner.invoke(cli, ["dashboard", "stop"])
    assert stopped.exit_code == 0, stopped.output
    assert "Dashboard stopped" in stopped.output
    assert seen_kills
