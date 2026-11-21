"""Tests for sync execution (issue #2: no implicit infra/sync-skills.py fallback).

The workspace contract (``config.py`` / ``importer.py``) only carries
``skills/`` + ``repos/`` and never ``infra/``. Sync must work as a native
copy and must not fall back to searching for a legacy ``infra/sync-skills.py``.
"""

from __future__ import annotations

from pathlib import Path

import skillreg.config as cfgmod
import skillreg.services.sync_manager as sync_manager


def _configure(tmp_path, monkeypatch, *, skill_names: list[str] | None = None):
    fake_home = tmp_path / "isolated-home"
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

    cfg_path = tmp_path / "config.json"
    monkeypatch.setattr(cfgmod, "CONFIG_FILE", cfg_path)
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", cfg_path.parent)
    monkeypatch.setattr(sync_manager, "_PROJECTS_DIR", tmp_path / "projects")
    monkeypatch.setattr(sync_manager, "_PROJECTS_FILE", tmp_path / "projects" / "projects.json")

    # Valid workspace: only skills/ + repos/ (no infra/).
    workspace = tmp_path / "workspace"
    (workspace / "skills").mkdir(parents=True)
    (workspace / "repos").mkdir(parents=True)
    for name in skill_names or []:
        skill_dir = workspace / "skills" / name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Test\n---\n\n# {name}\n",
            encoding="utf-8",
        )

    cfg = cfgmod.load_config()
    cfg.workspace_path = str(workspace)
    cfgmod.save_config(cfg)
    return workspace


def test_execute_sync_empty_workspace_noop(tmp_path, monkeypatch):
    """An empty workspace (no infra/) syncs as an explainable success no-op."""
    workspace = _configure(tmp_path, monkeypatch)
    assert not (workspace / "infra").exists()

    target = tmp_path / "target-skills"
    dry_run_result = sync_manager.execute_sync(str(target), dry_run=True)
    assert dry_run_result["success"] is True
    assert "workspace has no skills" in dry_run_result["stdout"]

    result = sync_manager.execute_sync(str(target))
    assert result["success"] is True
    assert result["stdout"] == dry_run_result["stdout"]


def test_execute_sync_unmatched_skill_noop(tmp_path, monkeypatch):
    """An unmatched skill filter is an explainable success no-op."""
    _configure(tmp_path, monkeypatch, skill_names=["alpha"])

    target = tmp_path / "target-skills"
    result = sync_manager.execute_sync(str(target), skills=["nope"])
    assert result["success"] is True
    assert "no matching skills in workspace: nope" in result["stdout"]
    assert not (target / "nope").exists()

    dry_run_result = sync_manager.execute_sync(str(target), dry_run=True, skills=["nope"])
    assert dry_run_result == result


def test_execute_sync_target_filter_unmatched_noop(tmp_path, monkeypatch):
    """A target whitelist that matches nothing is a no-op, not a script lookup."""
    _configure(tmp_path, monkeypatch, skill_names=["alpha"])
    target = tmp_path / "target-skills"
    cfg = cfgmod.load_config()
    cfg.target_skill_filters[str(target)] = ["ghost"]
    cfgmod.save_config(cfg)

    result = sync_manager.execute_sync(str(target))
    assert result["success"] is True
    assert "no matching skills in workspace: ghost" in result["stdout"]
    assert not (target / "alpha").exists()


def test_execute_sync_native_copy_without_infra(tmp_path, monkeypatch):
    """A matching skill still syncs via native copy when infra/ is absent."""
    workspace = _configure(tmp_path, monkeypatch, skill_names=["alpha"])
    assert not (workspace / "infra").exists()

    target = tmp_path / "target-skills"
    result = sync_manager.execute_sync(str(target))
    assert result["success"] is True
    assert "Synced 1 skill(s)" in result["stdout"]
    assert (target / "alpha" / "SKILL.md").is_file()


def test_execute_sync_dry_run_matching_skill(tmp_path, monkeypatch):
    """dry-run previews matching skills without touching the target."""
    _configure(tmp_path, monkeypatch, skill_names=["alpha"])

    target = tmp_path / "target-skills"
    result = sync_manager.execute_sync(str(target), dry_run=True)
    assert result["success"] is True
    assert f"Would sync alpha -> {target}" in result["stdout"]
    assert not (target / "alpha").exists()


def test_no_legacy_script_search(tmp_path, monkeypatch):
    """The module no longer searches for a legacy infra/sync-skills.py script."""
    assert not hasattr(sync_manager, "_find_sync_script")


def test_sync_config_preserves_custom_target_names_and_ids(tmp_path, monkeypatch):
    """get_sync_config must keep saved custom target names and stable IDs."""
    from skillreg.services import sync_targets

    _configure(tmp_path, monkeypatch, skill_names=["alpha"])
    target_dir = tmp_path / "home" / ".claude" / "skills"
    saved = sync_targets.add_target("my-claude", str(target_dir))

    config = sync_manager.get_sync_config()
    assert len(config["targets"]) == 1
    entry = config["targets"][0]
    assert entry["id"] == saved["id"]
    assert entry["name"] == "my-claude"
    assert entry["label"] == "my-claude"
    assert entry["path"] == saved["path"]


def test_execute_sync_rejects_ambiguous_or_unknown_names_without_writing_cwd(tmp_path, monkeypatch):
    """Ambiguous target names, unknown names, and relative paths must never write to CWD."""
    import pytest
    from skillreg.services import sync_files, sync_targets

    _configure(tmp_path, monkeypatch, skill_names=["alpha"])
    cwd = tmp_path / "server-cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    first = sync_targets.add_target("claude", str(tmp_path / "t1" / ".claude" / "skills"))
    second = sync_targets.add_target("claude", str(tmp_path / "t2" / ".claude" / "skills"))

    with pytest.raises(sync_files.SyncError) as exc_ambiguous:
        sync_manager.execute_sync("claude", skills=["alpha"])
    assert exc_ambiguous.value.code == "ambiguous-target"
    assert not (cwd / "claude").exists()

    with pytest.raises(sync_files.SyncError) as exc_missing:
        sync_manager.execute_sync("missing-target-name", skills=["alpha"])
    assert exc_missing.value.code == "not-found"
    assert not (cwd / "missing-target-name").exists()

    with pytest.raises(sync_files.SyncError) as exc_rel:
        sync_manager.execute_sync(".claude/skills", skills=["alpha"])
    assert exc_rel.value.code == "invalid"
    assert not (cwd / ".claude").exists()

    # Installing by stable target ID succeeds cleanly into the intended directory.
    res = sync_manager.execute_sync(first["id"], skills=["alpha"])
    assert res["success"] is True
    assert res["syncedCount"] == 1
    assert (tmp_path / "t1" / ".claude" / "skills" / "alpha" / "SKILL.md").is_file()
    assert not (tmp_path / "t2" / ".claude" / "skills" / "alpha").exists()

    # Installing by exact path also resolves cleanly despite duplicate display names.
    res2 = sync_manager.execute_sync(second["path"], skills=["alpha"])
    assert res2["success"] is True
    assert (tmp_path / "t2" / ".claude" / "skills" / "alpha" / "SKILL.md").is_file()


def test_execute_sync_ignores_venv_node_modules_and_pyc_consistently(tmp_path, monkeypatch):
    """Skills with .venv/node_modules (including internal symlinks) sync cleanly and report synced."""
    import sys

    workspace = _configure(tmp_path, monkeypatch, skill_names=["cli-tool"])
    skill_dir = workspace / "skills" / "cli-tool"
    (skill_dir / ".venv" / "bin").mkdir(parents=True)
    (skill_dir / ".venv" / "bin" / "python").symlink_to(sys.executable)
    (skill_dir / "node_modules" / ".bin").mkdir(parents=True)
    (skill_dir / "node_modules" / ".bin" / "pkg").symlink_to(skill_dir / "SKILL.md")
    (skill_dir / "helper.pyc").write_bytes(b"\x00\x01")
    (skill_dir / "tool.py").write_text("print('ok')\n", encoding="utf-8")

    target = tmp_path / "installed-skills"
    res = sync_manager.execute_sync(str(target), skills=["cli-tool"])
    assert res["success"] is True
    assert res["syncedCount"] == 1
    assert (target / "cli-tool" / "tool.py").is_file()
    assert not (target / "cli-tool" / ".venv").exists()
    assert not (target / "cli-tool" / "node_modules").exists()
    assert not (target / "cli-tool" / "helper.pyc").exists()

    rows = sync_manager.get_sync_status(target=str(target), skill="cli-tool")
    assert rows[0]["status"] == "synced"
    diff = sync_manager.get_skill_diff("cli-tool", str(target))
    assert all(row["status"] == "unchanged" for row in diff)


def test_execute_sync_refreshes_stale_skill_cache(tmp_path, monkeypatch):
    """Installing a newly created skill must bypass stale get_all cache."""
    from skillreg.services import skill_registry

    workspace = _configure(tmp_path, monkeypatch, skill_names=["alpha"])
    # Warm the cache before creating the new skill.
    assert [s["name"] for s in skill_registry.get_all(workspace)["skills"]] == ["alpha"]

    fresh = workspace / "skills" / "fresh-skill"
    fresh.mkdir()
    (fresh / "SKILL.md").write_text(
        "---\nname: fresh-skill\ndescription: Fresh\n---\n\n# Fresh\n",
        encoding="utf-8",
    )

    target = tmp_path / "target-skills"
    result = sync_manager.execute_sync(str(target), skills=["fresh-skill"])
    assert result["success"] is True
    assert result["syncedCount"] == 1
    assert (target / "fresh-skill" / "SKILL.md").is_file()


def test_replace_directory_fallback_on_unsupported_filesystem_and_rollback(tmp_path, monkeypatch):
    """Overwrite falls back to backup-swap when atomic exchange is unsupported, and rolls back on failure."""
    import os
    import pytest
    from skillreg.services import sync_files

    workspace = _configure(tmp_path, monkeypatch, skill_names=["alpha"])
    target = tmp_path / "target-skills"
    sync_manager.execute_sync(str(target), skills=["alpha"])

    # Modify source and simulate unsupported filesystem for atomic exchange.
    (workspace / "skills" / "alpha" / "SKILL.md").write_text(
        "---\nname: alpha\ndescription: Updated\n---\n\n# alpha v2\n",
        encoding="utf-8",
    )

    def unsupported(*_args):
        raise sync_files.SyncError("unsupported", "unsupported-filesystem")

    monkeypatch.setattr(sync_files, "exchange_directories", unsupported)
    res = sync_manager.execute_sync(str(target), skills=["alpha"])
    assert res["success"] is True
    assert "# alpha v2" in (target / "alpha" / "SKILL.md").read_text(encoding="utf-8")
    assert list(target.glob(".skillreg-backup-*")) == []
    assert list(target.glob(".skillreg-stage-*")) == []

    # Simulate failure on second os.rename during fallback -> original must be restored.
    (workspace / "skills" / "alpha" / "SKILL.md").write_text(
        "---\nname: alpha\ndescription: Broken\n---\n\n# alpha v3\n",
        encoding="utf-8",
    )
    real_rename = os.rename
    calls = {"count": 0}

    def fail_second_rename(src, dst):
        calls["count"] += 1
        if calls["count"] == 2:
            raise OSError("disk full during swap")
        return real_rename(src, dst)

    monkeypatch.setattr(os, "rename", fail_second_rename)
    with pytest.raises(OSError, match="disk full"):
        sync_manager.execute_sync(str(target), skills=["alpha"])
    assert "# alpha v2" in (target / "alpha" / "SKILL.md").read_text(encoding="utf-8")


def test_install_lock_retries_brief_contention_and_reports_busy(tmp_path, monkeypatch):
    """Brief lock contention serializes cleanly; prolonged contention raises target-busy."""
    import fcntl
    import threading
    import time
    import pytest
    from skillreg.services import sync_files

    workspace = _configure(tmp_path, monkeypatch, skill_names=["alpha"])
    target = tmp_path / "target-skills"
    target.mkdir(parents=True)
    lock_file = target / ".skillreg-sync.lock"
    snapshot, bundle, digest = sync_files.make_bundle(workspace / "skills" / "alpha")

    with lock_file.open("a+") as held:
        fcntl.flock(held.fileno(), fcntl.LOCK_EX)

        def release_soon():
            time.sleep(0.12)
            fcntl.flock(held.fileno(), fcntl.LOCK_UN)

        releaser = threading.Thread(target=release_soon)
        releaser.start()
        result = sync_files.install({
            "path": str(target),
            "name": "alpha",
            "bundle": bundle,
            "bundleDigest": digest,
            "sourceDigest": snapshot["digest"],
            "force": True,
            "workspaceId": str(workspace),
            "runId": "r1",
            "lockTimeout": 1.0,
        })
        releaser.join()
        assert result["status"] == "synced"

    with lock_file.open("a+") as held:
        fcntl.flock(held.fileno(), fcntl.LOCK_EX)
        with pytest.raises(sync_files.SyncError) as exc_busy:
            sync_files.install({
                "path": str(target),
                "name": "alpha",
                "bundle": bundle,
                "bundleDigest": digest,
                "sourceDigest": snapshot["digest"],
                "force": True,
                "workspaceId": str(workspace),
                "runId": "r2",
                "lockTimeout": 0.05,
            })
        assert exc_busy.value.code == "target-busy"


def test_project_status_expands_discovered_agent_dirs(tmp_path, monkeypatch):
    """include_projects status checks discovered agent skill dirs so UI reflects installed state."""
    _configure(tmp_path, monkeypatch, skill_names=["alpha"])
    project_root = tmp_path / "my-app"
    (project_root / ".claude").mkdir(parents=True)
    claude_skills = project_root / ".claude" / "skills"

    sync_manager.create_project("MyApp", [str(project_root)])

    before = sync_manager.get_sync_status(include_projects=True, skill="alpha")
    proj_rows_before = [r for r in before if r.get("_project") == "MyApp"]
    assert len(proj_rows_before) == 1
    assert proj_rows_before[0]["target"] == str(claude_skills.resolve())
    assert proj_rows_before[0]["status"] == "missing"

    sync_manager.execute_sync(str(claude_skills), skills=["alpha"])

    after = sync_manager.get_sync_status(include_projects=True, skill="alpha")
    proj_rows_after = [r for r in after if r.get("_project") == "MyApp"]
    assert proj_rows_after[0]["target"] == str(claude_skills.resolve())
    assert proj_rows_after[0]["status"] == "synced"
