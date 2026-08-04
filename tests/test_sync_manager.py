"""Tests for sync execution (issue #2: no implicit infra/sync-skills.py fallback).

The workspace contract (``config.py`` / ``importer.py``) only carries
``skills/`` + ``repos/`` and never ``infra/``. Sync must work as a native
copy and must not fall back to searching for a legacy ``infra/sync-skills.py``.
"""

from __future__ import annotations

import skillreg.config as cfgmod
import skillreg.services.sync_manager as sync_manager


def _configure(tmp_path, monkeypatch, *, skill_names: list[str] | None = None):
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
