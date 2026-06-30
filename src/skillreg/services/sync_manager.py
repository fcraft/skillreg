"""Sync manager service — ported from agent-hub ``sync-manager.js``.

Handles target configuration CRUD, project registry, and sync execution.
Delegates actual sync logic to ``sync-skills.py`` via subprocess.
"""

from __future__ import annotations

import filecmp
import json
import shutil
import subprocess
import uuid
from pathlib import Path

from .skill_registry import get_all, get_skill

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
        label = _target_display_name(Path(t))
        skills = _target_filter_for(cfg, t)
        result.append({
            "name": label,
            "path": t,
            "label": label,
            "skills": skills,
            "skillCount": len(skills),
            "status": {},
        })
    return result


def get_sync_config(cfg: SkillregConfig | None = None) -> dict:
    """Return a synthesized sync config compatible with the dashboard."""
    if cfg is None:
        cfg = load_config()
    return {
        "schema_version": 2,
        "targets": [
            {
                "name": _target_display_name(Path(t)),
                "path": t,
                "label": _target_display_name(Path(t)),
                "skills": _target_filter_for(cfg, t),
            }
            for t in cfg.targets
        ],
        "sources": [
            {"path": "skills", "mode": "scan"},
            {"path": "repos", "mode": "scan"},
        ],
        "exclude_dirs": [
            "__pycache__", ".git", ".venv", "infra", "specs", "logs",
            "node_modules", "venv",
        ],
        "exclude_files": [".DS_Store", "*.pyc"],
        "manifest": {
            "enabled": True,
            "skip_unchanged": True,
            "file": ".sync-manifest.json",
        },
    }


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
    target = _resolve_config_target(cfg, name)
    if target is None:
        raise ValueError(f'Target "{name}" not found')
    cfg.targets.remove(target)
    _remove_target_filter(cfg, target)
    save_config(cfg)


def rename_target(old_name: str, new_name: str) -> dict:
    """Rename a target."""
    cfg = load_config()
    target = _resolve_config_target(cfg, old_name)
    if target is None:
        raise ValueError(f'Target "{old_name}" not found')
    if _resolve_config_target(cfg, new_name) is not None:
        raise ValueError(f'Target "{new_name}" already exists')
    idx = cfg.targets.index(target)
    cfg.targets[idx] = new_name
    _rename_target_filter(cfg, target, new_name)
    save_config(cfg)
    return {"name": new_name, "path": new_name}


def update_target_skills(target: str, skills: list[str]) -> dict:
    """Persist the skill whitelist for a configured sync target."""
    cfg = load_config()
    target_path = _resolve_config_target(cfg, target)
    if target_path is None:
        raise ValueError(f"Unknown target: {target}")
    normalized_skills = list(dict.fromkeys(skills))
    cfg.target_skill_filters[target_path] = normalized_skills
    save_config(cfg)
    return {
        "target": target,
        "path": target_path,
        "skills": normalized_skills,
        "skillCount": len(normalized_skills),
    }


def get_sync_status(
    target: str | None = None,
    include_projects: bool = False,
    skill: str | None = None,
) -> list[dict]:
    """Get per-target per-skill sync status for dashboard badges."""
    cfg = load_config()
    workspace = _workspace_from_config(cfg)
    data = get_all(workspace)
    target_paths = _selected_targets(cfg.targets, target)
    source_skills = data["skills"]
    if skill:
        source_skills = [s for s in source_skills if s["name"] == skill]

    rows: list[dict] = []
    for target_path in target_paths:
        for item in source_skills:
            rows.append({
                "target": target_path,
                "name": item["name"],
                "status": _skill_status(workspace, target_path, item),
            })

    if include_projects:
        project_map = _read_projects().get("projects", {})
        for project_id, project in project_map.items():
            for target_path in project.get("targets", []):
                if target and Path(target_path).expanduser() != Path(target).expanduser():
                    continue
                for item in source_skills:
                    rows.append({
                        "target": target_path,
                        "name": item["name"],
                        "status": _skill_status(workspace, target_path, item),
                        "_project": project.get("name"),
                        "_projectId": project_id,
                    })
    return rows


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
    cfg = load_config()
    workspace = _workspace_from_config(cfg)
    target_config_path = _resolve_config_target(cfg, target) or target
    target_path = Path(target_config_path).expanduser()
    target_path.mkdir(parents=True, exist_ok=True)
    selected_names = skills if skills is not None else _target_filter_for(cfg, target_config_path)
    selected_skills = _select_source_skills(workspace, selected_names or None)

    if dry_run:
        return {
            "success": True,
            "stdout": "\n".join(f"Would sync {item['name']} -> {target_path}" for item in selected_skills),
            "stderr": "",
        }

    copied = 0
    for item in selected_skills:
        source_dir = workspace / item["path"]
        destination = target_path / item["name"]
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(
            source_dir,
            destination,
            ignore=shutil.ignore_patterns(".git", "__pycache__", ".DS_Store", "Thumbs.db", "._*"),
        )
        copied += 1

    if copied > 0:
        return {
            "success": True,
            "stdout": f"Synced {copied} skill(s) to {target_path}",
            "stderr": "",
        }

    # Build the sync command
    sync_script = _find_sync_script()
    args = [
        "python3", str(sync_script),
        "--target", str(target_path),
        "--repo-root", str(workspace),
    ]
    if dry_run:
        args.append("--dry-run")
    if selected_names:
        args.extend(selected_names)

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


def get_skill_presence(skill: str) -> dict:
    """Return target presence map for a skill."""
    cfg = load_config()
    workspace = _workspace_from_config(cfg)
    item = get_skill(workspace, skill)
    if not item:
        raise ValueError(f"Unknown skill: {skill}")
    targets = {
        target_path: _skill_status(workspace, target_path, item)
        for target_path in cfg.targets
    }
    return {"skill": skill, "targets": targets}


def list_target_skills(target: str) -> dict:
    """List skills currently present in a target directory."""
    cfg = load_config()
    workspace = _workspace_from_config(cfg)
    target_config_path = _resolve_config_target(cfg, target) or target
    target_path = Path(target_config_path).expanduser()
    source_lookup = {item["name"]: item for item in get_all(workspace)["skills"]}
    skills: list[dict] = []
    if target_path.is_dir():
        for entry in sorted(target_path.iterdir(), key=lambda item: item.name.lower()):
            if not entry.is_dir():
                continue
            managed = entry.name in source_lookup
            status = "unmanaged"
            if managed:
                status = _skill_status(workspace, str(target_path), source_lookup[entry.name])
            skills.append({
                "name": entry.name,
                "path": str(entry),
                "managed": managed,
                "status": status,
            })
    return {
        "target": str(target_path),
        "configuredSkills": _target_filter_for(cfg, target_config_path),
        "skills": skills,
    }


def get_skill_diff(skill: str, target: str) -> list[dict]:
    """Return file-level diff summary between workspace skill and target skill."""
    cfg = load_config()
    workspace = _workspace_from_config(cfg)
    item = get_skill(workspace, skill)
    if not item:
        raise ValueError(f"Unknown skill: {skill}")
    source_dir = workspace / item["path"]
    target_dir = Path(_resolve_config_target(cfg, target) or target).expanduser() / skill
    return _diff_dirs(source_dir, target_dir)


def remove_skill_from_target(skill: str, target: str, force: bool = False) -> dict:
    """Remove a skill directory from a target."""
    cfg = load_config()
    target_dir = Path(_resolve_config_target(cfg, target) or target).expanduser() / skill
    if not target_dir.exists():
        return {"success": True, "removed": False, "target": str(target_dir.parent), "skill": skill}
    shutil.rmtree(target_dir)
    return {
        "success": True,
        "removed": True,
        "target": str(target_dir.parent),
        "skill": skill,
        "force": force,
    }


def get_target_file(skill: str, target: str, rel_path: str) -> dict:
    """Read a file from a synced target skill."""
    cfg = load_config()
    base = Path(_resolve_config_target(cfg, target) or target).expanduser() / skill
    file_path = (base / rel_path).resolve()
    if not str(file_path).startswith(str(base.resolve())):
        raise ValueError("Invalid file path")
    if not file_path.exists():
        return {"exists": False, "path": rel_path}
    if not file_path.is_file():
        raise ValueError("Path is not a file")
    raw = file_path.read_bytes()
    try:
        content = raw.decode("utf-8")
        binary = False
    except UnicodeDecodeError:
        content = None
        binary = True
    result = {"exists": True, "size": len(raw)}
    if binary:
        result["binary"] = True
    else:
        result["content"] = content
        result["language"] = file_path.suffix.lstrip(".") or "text"
    return result


def _find_sync_script() -> Path:
    """Find the sync-skills.py script."""
    candidates = [
        Path(__file__).resolve().parents[3] / "infra" / "sync-skills.py",
        Path.cwd() / "infra" / "sync-skills.py",
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


def refresh_target(target: str) -> dict:
    """Refresh target status snapshot."""
    return {
        "target": str(Path(target).expanduser()),
        "skills": list_target_skills(target)["skills"],
    }


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


def _workspace_from_config(cfg: SkillregConfig | None = None) -> Path:
    cfg = cfg or load_config()
    if cfg.workspace_path:
        return Path(cfg.workspace_path).expanduser().resolve()
    return Path.cwd()


def _select_source_skills(workspace: Path, skills: list[str] | None) -> list[dict]:
    items = get_all(workspace)["skills"]
    if not skills:
        return items
    skill_set = set(skills)
    return [item for item in items if item["name"] in skill_set]


def _skill_status(workspace: Path, target: str, item: dict) -> str:
    source_dir = workspace / item["path"]
    target_dir = Path(target).expanduser() / item["name"]
    if not target_dir.exists():
        return "missing"
    return "synced" if _dirs_equal(source_dir, target_dir) else "modified"


def _selected_targets(targets: list[str], target: str | None) -> list[str]:
    if not target:
        return list(targets)
    resolved = Path(target).expanduser()
    return [
        t
        for t in targets
        if Path(t).expanduser() == resolved
        or t == target
        or _target_display_name(Path(t)) == target
    ] or [target]


def _resolve_config_target(cfg: SkillregConfig, target: str) -> str | None:
    if target in cfg.targets:
        return target
    target_path = Path(target).expanduser()
    for item in cfg.targets:
        item_path = Path(item).expanduser()
        if item_path == target_path or _target_display_name(item_path) == target:
            return item
    return None


def _target_filter_for(cfg: SkillregConfig, target: str) -> list[str]:
    for key in _target_filter_keys(target):
        skills = cfg.target_skill_filters.get(key)
        if skills is not None:
            return list(skills)
    return []


def _target_filter_keys(target: str) -> list[str]:
    path = Path(target).expanduser()
    keys = [target, str(path), _target_display_name(path)]
    resolved = str(path.resolve()) if path.exists() else None
    if resolved:
        keys.append(resolved)
    return list(dict.fromkeys(keys))


def _remove_target_filter(cfg: SkillregConfig, target: str) -> None:
    for key in _target_filter_keys(target):
        cfg.target_skill_filters.pop(key, None)


def _rename_target_filter(cfg: SkillregConfig, old_target: str, new_target: str) -> None:
    skills = _target_filter_for(cfg, old_target)
    _remove_target_filter(cfg, old_target)
    if skills:
        cfg.target_skill_filters[new_target] = skills


def _dirs_equal(source: Path, target: Path) -> bool:
    if not source.is_dir() or not target.is_dir():
        return False
    comparison = filecmp.dircmp(source, target, ignore=[".git", "__pycache__", ".DS_Store", "Thumbs.db"])
    if comparison.left_only or comparison.right_only or comparison.diff_files or comparison.funny_files:
        return False
    return all(
        _dirs_equal(Path(source, name), Path(target, name))
        for name in comparison.common_dirs
    )


def _diff_dirs(source: Path, target: Path) -> list[dict]:
    source_files = _walk_files(source) if source.is_dir() else {}
    target_files = _walk_files(target) if target.is_dir() else {}
    all_paths = sorted(set(source_files) | set(target_files))
    rows = []
    for rel_path in all_paths:
        if rel_path not in target_files:
            status = "removed"
        elif rel_path not in source_files:
            status = "added"
        elif source_files[rel_path] == target_files[rel_path]:
            status = "unchanged"
        else:
            status = "modified"
        rows.append({"path": rel_path, "status": status})
    return rows


def _walk_files(root: Path) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    for file_path in sorted(root.rglob("*")):
        if not file_path.is_file():
            continue
        if any(part in {".git", "__pycache__"} for part in file_path.parts):
            continue
        rel_path = str(file_path.relative_to(root)).replace("\\", "/")
        result[rel_path] = file_path.read_bytes()
    return result


def _target_name(path: Path) -> str:
    return path.name or str(path)


def _target_display_name(path: Path) -> str:
    resolved = path.expanduser()
    normalized = [part for part in resolved.parts if part not in ("/", "")]
    if len(normalized) >= 2 and normalized[-1] == "skills":
        parent = normalized[-2]
        if parent.startswith(".") and len(parent) > 1:
            return parent[1:]
        return parent
    return _target_name(resolved)
