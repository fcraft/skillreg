"""Builtin skill injection — injects skillreg's own SKILL.md into the workspace.

Per PRD §2.4, the skillreg self-skill is baked into the Python package via
``importlib.resources`` and injected into the workspace's ``.skillreg/builtin/skillreg-skill/``
directory on startup. This directory is gitignored (does not enter workspace git).
"""

from __future__ import annotations

import shutil
from pathlib import Path


def inject_self_skill(workspace: Path) -> Path | None:
    """Copy skillreg's builtin SKILL.md to workspace/.skillreg/builtin/skillreg-skill/.

    Returns the target directory path, or None if the workspace doesn't exist.
    """
    if not workspace.is_dir():
        return None

    target = workspace / ".skillreg" / "builtin" / "skillreg-skill"
    target.mkdir(parents=True, exist_ok=True)

    # Read builtin SKILL.md from package resources
    try:
        _copy_builtin_from_package(target)
    except Exception:
        # Fallback: copy from development path
        _copy_builtin_from_dev(target)

    return target


def _copy_builtin_from_package(target: Path) -> None:
    """Copy from importlib.resources (installed package)."""
    from importlib.resources import files as resource_files

    source = resource_files("skillreg") / "builtin" / "skillreg-skill"
    if source.is_dir():
        _copy_tree(source, target)


def _copy_builtin_from_dev(target: Path) -> None:
    """Copy from development source tree."""
    dev_source = Path(__file__).resolve().parent.parent / "builtin" / "skillreg-skill"
    if dev_source.is_dir():
        _copy_tree(dev_source, target)


def _copy_tree(src: Path, dst: Path) -> None:
    """Recursively copy directory contents from src to dst."""
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def init_self_skill(workspace_path: str | None) -> Path | None:
    """Entry point: inject self-skill if workspace is configured."""
    if not workspace_path:
        return None
    ws = Path(workspace_path).expanduser().resolve()
    if not ws.is_dir():
        return None
    return inject_self_skill(ws)
