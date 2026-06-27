"""Sync manager service — ported from agent-hub ``sync-manager.js``.

Handles target configuration CRUD, project registry, and sync execution.
Delegates actual sync logic to ``sync-skills.py`` via subprocess.
"""

from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path

from ..config import load_config, save_config, SkillregConfig

# ── project registry ───────────────────────────────────────────────────────

_PROJECTS_DIR = Path.home() / ".skillreg"
_PROJECTS_FILE = _PROJECTS_DIR / "projects.json"


def _read_projects() -> dict[str, dict]:
    if not _PROJECTS_FILE.exists():
        return {"projects": {}}
    try:
        data = json.loads(_PROJECTS_FILE.read_text(encoding="utf-8"))
        return data if "projects" in data else {"projects": {}}
    except (json.JSONDecodeError, OSError):
        return {"projects": {}}


def _write_projects(data: dict) -> None:
    _PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    _PROJECTS_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
    )


# ── target management ──────────────────────────────────────────────────────


def get_targets(cfg: SkillregConfig | None = None) -> list[dict]:
    """Get targets with their skill status overview.

    In v1, targets are stored in ``~/.skillreg/config.json`` (simple list of
    paths with optional names). The response includes sync status per target.
    """
    if cfg is None:
        cfg = load_config()
    result = []
    for t in cfg.targets:
        # For now return basic target info; full status comes from sync engine
        result.append({
            "name": t,
            "path": t,
            "status": {},
        })
    return result


def add_target(name: str, path: str) -> dict:
    """Add a new sync target."""
    cfg = load_config()
    if path in cfg.targets:
        raise ValueError(f'Target "{path}" already exists')
    cfg.targets.append(path)
    save_config(cfg)
    return {"name": name, "path": path}


def remove_target(name: str) -> None:
    """Remove a sync target by name or path."""
    cfg = load_config()
    if name not in cfg.targets:
        raise ValueError(f'Target "{name}" not found')
    cfg.targets.remove(name)
    save_config(cfg)


def rename_target(old_name: str, new_name: str) -> dict:
    """Rename a target."""
    cfg = load_config()
    if old_name not in cfg.targets:
        raise ValueError(f'Target "{old_name}" not found')
    if new_name in cfg.targets:
        raise ValueError(f'Target "{new_name}" already exists')
    idx = cfg.targets.index(old_name)
    cfg.targets[idx] = new_name
    save_config(cfg)
    return {"name": new_name, "path": new_name}


# ── project management ─────────────────────────────────────────────────────


def list_projects() -> list[dict]:
    data = _read_projects()
    return list(data.get("projects", {}).values())


def get_project(pid: str) -> dict | None:
    data = _read_projects()
    projects = data.get("projects", {})
    entry = projects.get(pid)
    if entry:
        return entry
    # Try case-insensitive name match
    for p in projects.values():
        if p.get("name", "").lower() == pid.lower():
            return p
    return None


def create_project(name: str, targets: list[str]) -> dict:
    data = _read_projects()
    pid = str(uuid.uuid4())
    entry = {
        "id": pid,
        "name": name,
        "targets": [str(Path(t).expanduser()) for t in targets],
        "created_at": _now_iso(),
    }
    data.setdefault("projects", {})[pid] = entry
    _write_projects(data)
    return entry


def add_project_target(pid: str, path: str) -> dict:
    data = _read_projects()
    entry, project_id = _find_project(data, pid)
    if not entry:
        raise ValueError(f'Project not found: {pid}')
    resolved = str(Path(path).expanduser())
    targets = entry.setdefault("targets", [])
    if resolved not in targets:
        targets.append(resolved)
    _write_projects(data)
    return entry


def remove_project_target(pid: str, path: str) -> dict:
    data = _read_projects()
    entry, project_id = _find_project(data, pid)
    if not entry:
        raise ValueError(f'Project not found: {pid}')
    resolved = str(Path(path).expanduser())
    entry["targets"] = [t for t in entry.get("targets", []) if t != resolved]
    _write_projects(data)
    return entry


def delete_project(pid: str) -> None:
    data = _read_projects()
    _, project_id = _find_project(data, pid)
    if not project_id:
        raise ValueError(f'Project not found: {pid}')
    del data["projects"][project_id]
    _write_projects(data)


# ── sync execution ─────────────────────────────────────────────────────────


def execute_sync(target: str, dry_run: bool = False, skills: list[str] | None = None) -> dict:
    """Execute sync via sync-skills.py subprocess.

    In v1 this delegates to the sync-skills.py script. Once sync-skills.py
    is adapted for workspace paths, this will use the workspace path from config.
    """
    # Resolve target: look up in config to get resolved path
    cfg = load_config()
    if cfg.workspace_path:
        workspace = Path(cfg.workspace_path).expanduser()
    else:
        workspace = Path.cwd()

    # For now, use the target path directly (it's already absolute from config)
    target_path = Path(target).expanduser()

    # Build the sync command
    sync_script = _find_sync_script()
    args = [
        "python3", str(sync_script),
        "--target", str(target_path),
        "--repo-root", str(workspace),
    ]
    if dry_run:
        args.append("--dry-run")
    if skills:
        args.extend(skills)

    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=60,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "stdout": "", "stderr": "Sync timed out after 60s"}
    except FileNotFoundError:
        return {"success": False, "stdout": "", "stderr": "sync-skills.py not found"}


def _find_sync_script() -> Path:
    """Find the sync-skills.py script."""
    # Check in agent-hub infra/
    candidates = [
        Path.home() / "Code/project_kex/agent-hub/infra/sync-skills.py",
        Path(__file__).resolve().parents[4] / "infra" / "sync-skills.py",  # agent-hub-kex
        Path(__file__).resolve().parents[3] / "agent-hub" / "infra" / "sync-skills.py",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("sync-skills.py not found in any expected location")


# ── agent dir discovery ────────────────────────────────────────────────────


_AGENT_CONVENTIONS: list[tuple[str, str]] = [
    (".claude/skills", "claude"),
    (".tclaude/skills", "tclaude"),
    (".codebuddy/skills", "codebuddy"),
    (".codex/skills", "codex"),
    (".tcodex/skills", "tcodex"),
    (".agents/skills", "agents"),
    (".agent/skills", "agent"),
]


def discover_agent_dirs(root_path: str) -> list[dict]:
    """Scan a directory for agent hub directories."""
    root = Path(root_path).expanduser().resolve()
    if not root.is_dir():
        return []
    found = []
    for rel, agent_name in _AGENT_CONVENTIONS:
        agent_dir = root / rel.split("/")[0]
        if agent_dir.is_dir():
            found.append({"agent": agent_name, "path": str(root / rel)})
    return found


def discover_home_agent_dirs() -> list[dict]:
    """Auto-discover agent dirs under ~/."""
    home = Path.home()
    found = []
    for rel, agent_name in _AGENT_CONVENTIONS:
        agent_dir = home / rel.split("/")[0]
        if agent_dir.is_dir():
            found.append({
                "agent": agent_name,
                "rel_path": rel,
                "path": str(home / rel),
            })
    return found


# ── helpers ────────────────────────────────────────────────────────────────


def _find_project(data: dict, pid: str) -> tuple[dict | None, str | None]:
    projects = data.get("projects", {})
    if pid in projects:
        return projects[pid], pid
    for k, p in projects.items():
        if p.get("name", "").lower() == pid.lower():
            return p, k
    return None, None


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
