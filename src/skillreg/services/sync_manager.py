"""Sync manager service.

Handles target configuration CRUD, project registry, and sync execution.
Copies selected skills directly from the workspace into sync targets.
"""

from __future__ import annotations

import filecmp
import json
import shutil
import uuid
from pathlib import Path

from .skill_registry import get_all, get_skill
from . import agent_catalog, sync_targets, sync_files

from ..config import load_config, save_config, SkillregConfig

# ── project registry ───────────────────────────────────────────────────────

from .. import config as config_module

_PROJECTS_DIR = config_module.CONFIG_DIR
_PROJECTS_FILE = _PROJECTS_DIR / "projects.json"


def _read_projects() -> dict[str, dict]:
    if not _PROJECTS_FILE.exists():
        return {"projects": {}}
    try:
        data = json.loads(_PROJECTS_FILE.read_text(encoding="utf-8"))
        if "projects" not in data:
            return {"projects": {}}
        for project in data["projects"].values():
            if "targetIds" in project:
                targets = []
                for identifier in project["targetIds"]:
                    try:
                        target = sync_targets.resolve_target(identifier)
                        targets.append(target["path"] if target["transport"] == "local" else target["id"])
                    except ValueError:
                        continue
                project["targets"] = targets
        return data
    except (json.JSONDecodeError, OSError):
        return {"projects": {}}


def _write_projects(data: dict) -> None:
    for project in data.get("projects", {}).values():
        identifiers = []
        for value in project.get("targets", []):
            try:
                target = sync_targets.resolve_target(value)
            except ValueError:
                target = sync_targets.add_target(sync_targets.display_name(value), value)
            identifiers.append(target["id"])
        project["targetIds"] = identifiers
    _PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    _PROJECTS_FILE.write_text(
        json.dumps({"projects": {key: {k: v for k, v in value.items() if k != "targets"} for key, value in data["projects"].items()}}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
    )


# ── target management ──────────────────────────────────────────────────────


def get_targets(cfg: SkillregConfig | None = None) -> list[dict]:
    """Get local sync targets (configured + enabled built-in agents)."""
    if cfg is None:
        cfg = load_config()
    result = []
    for record in sync_targets.target_records(cfg, include_builtin=True):
        if record["transport"] != "local":
            continue
        t = record["path"]
        label = record["name"]
        skills = _target_filter_for(cfg, t)
        result.append({
            "id": record["id"],
            "transport": "local",
            "name": label,
            "path": t,
            "label": label,
            "skills": skills,
            "skillCount": len(skills),
            "status": {},
            "builtin": bool(record.get("builtin", False)),
            "source": record.get("source", "custom"),
            "agentKind": record.get("agentKind"),
            "icon": record.get("icon") or agent_catalog.icon_for_agent(record.get("agentKind")),
            "detectedBy": record.get("detectedBy"),
            "exists": record.get("exists", Path(t).expanduser().is_dir()),
            "shared": bool(record.get("shared", False)),
            "readsShared": bool(record.get("readsShared", False)),
            "relPath": record.get("relPath"),
        })
    return result


def get_sync_config(cfg: SkillregConfig | None = None) -> dict:
    """Return a synthesized sync config compatible with the dashboard."""
    if cfg is None:
        cfg = load_config()
    targets = []
    for record in sync_targets.target_records(cfg, include_builtin=True):
        if record["transport"] != "local":
            continue
        t = record["path"]
        label = record["name"]
        targets.append({
            "id": record["id"],
            "name": label,
            "path": t,
            "label": label,
            "skills": _target_filter_for(cfg, t),
            "builtin": bool(record.get("builtin", False)),
            "source": record.get("source", "custom"),
            "agentKind": record.get("agentKind"),
            "icon": record.get("icon") or agent_catalog.icon_for_agent(record.get("agentKind")),
            "detectedBy": record.get("detectedBy"),
            "exists": record.get("exists", Path(t).expanduser().is_dir()),
            "shared": bool(record.get("shared", False)),
            "readsShared": bool(record.get("readsShared", False)),
            "relPath": record.get("relPath"),
        })
    return {
        "schema_version": 2,
        "targets": targets,
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


def add_target(name: str, path: str, agent_kind: str | None = None) -> dict:
    """Add a new sync target."""
    return sync_targets.add_target(name, path, agent_kind=agent_kind)


def remove_target(name: str) -> None:
    """Remove a sync target by name or path (or hide a built-in agent target)."""
    sync_targets.remove_target(name)


def rename_target(old_name: str, new_name: str) -> dict:
    """Rename a configured target's path."""
    cfg = load_config()
    target = _resolve_config_target(cfg, old_name)
    if target is None:
        raise ValueError(f'Target "{old_name}" not found')
    record = sync_targets.resolve_target(old_name, cfg=cfg)
    if record.get("builtin"):
        raise ValueError("Built-in agent target paths cannot be renamed; add a custom target instead")
    if _resolve_config_target(cfg, new_name) is not None:
        raise ValueError(f'Target "{new_name}" already exists')
    projects = _read_projects()
    record["path"] = new_name
    configured = sync_targets.configured_target_records(cfg)
    cfg.targets = [
        sync_targets._storable_record(record if item["id"] == record["id"] else item)
        for item in configured
    ]
    _rename_target_filter(cfg, target, new_name)
    save_config(cfg)
    for project in projects["projects"].values():
        project["targets"] = [new_name if item == target else item for item in project.get("targets", [])]
    if projects["projects"]:
        _write_projects(projects)
    return {"name": new_name, "path": new_name}


def update_target_skills(target: str, skills: list[str]) -> dict:
    """Persist the skill whitelist for a configured sync target."""
    cfg = load_config()
    target_path = _resolve_config_target(cfg, target)
    if target_path is None:
        raise ValueError(f"Unknown target: {target}")
    normalized_skills = list(dict.fromkeys(skills))
    sync_targets.update_target(target, skills=normalized_skills)
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
    target_paths = _selected_targets(cfg, target)
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
            for project_target in project.get("targets", []):
                discovered = discover_agent_dirs(project_target)
                effective_targets = (
                    [(entry["path"], entry["agent"], entry.get("icon")) for entry in discovered]
                    if discovered
                    else [(project_target, None, None)]
                )
                for eff_path, agent_name, agent_icon in effective_targets:
                    if target and Path(eff_path).expanduser() != Path(target).expanduser() and Path(project_target).expanduser() != Path(target).expanduser():
                        continue
                    for item in source_skills:
                        row = {
                            "target": eff_path,
                            "name": item["name"],
                            "status": _skill_status(workspace, eff_path, item),
                            "_project": project.get("name"),
                            "_projectId": project_id,
                            "_projectRoot": project_target,
                        }
                        if agent_name:
                            row["_agent"] = agent_name
                        if agent_icon:
                            row["_icon"] = agent_icon
                        rows.append(row)
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
        "targets": [t if any(r["id"] == t for r in sync_targets.target_records()) else str(Path(t).expanduser()) for t in targets],
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


def _extract_run_error(run: dict) -> str:
    if isinstance(run.get("error"), dict) and run["error"].get("message"):
        return str(run["error"]["message"])
    messages: list[str] = []
    for target_result in run.get("results") or []:
        if isinstance(target_result.get("error"), dict) and target_result["error"].get("message"):
            messages.append(str(target_result["error"]["message"]))
        for skill_result in target_result.get("skills") or []:
            err = skill_result.get("error")
            if isinstance(err, dict) and err.get("message"):
                messages.append(f"{skill_result.get('name', 'skill')}: {err['message']}")
    return "; ".join(messages) if messages else "Remote sync failed"


def _is_explicit_local_path(value: str) -> bool:
    if value == "~" or value.startswith("~/") or value.startswith("~\\"):
        return True
    try:
        return Path(value).expanduser().is_absolute()
    except OSError:
        return False


def _resolve_execution_target(cfg: SkillregConfig, target: str) -> tuple[dict | None, str]:
    if not isinstance(target, str) or not target.strip():
        raise sync_files.SyncError("Target path or ID is required", "invalid")
    cleaned = target.strip()
    try:
        definition = sync_targets.resolve_target(cleaned, cfg=cfg)
        return definition, definition["path"]
    except sync_files.SyncError as exc:
        if exc.code != "not-found":
            raise
    if not _is_explicit_local_path(cleaned):
        if "/" in cleaned or "\\" in cleaned or cleaned.startswith("."):
            raise sync_files.SyncError(
                f"Target path must be an absolute path or start with ~/: {cleaned}",
                "invalid",
            )
        raise sync_files.SyncError(
            f"Target not found: {cleaned}",
            "not-found",
        )
    return None, cleaned


def execute_sync(target: str, dry_run: bool = False, skills: list[str] | None = None) -> dict:
    """Execute sync from the workspace to a target directory.

    Native copy is the only execution path: each selected skill is copied
    directly from the workspace (``skills/`` / ``repos/``) into the target.
    When no skill matches, the call is a no-op that returns success with an
    explainable message; it never falls back to a legacy ``infra/sync-skills.py``.
    """
    cfg = load_config()
    definition, target_config_path = _resolve_execution_target(cfg, target)
    if definition and definition["transport"] == "ssh":
        from . import sync_runs
        planned = sync_runs.preview([definition["id"]], skills)
        if dry_run:
            return {"success": True, "stdout": json.dumps(planned, ensure_ascii=False), "stderr": ""}
        run = sync_runs.create_run(planned["id"], background=False)
        succeeded = run["state"] == "succeeded"
        return {
            "success": succeeded,
            "stdout": json.dumps(run, ensure_ascii=False),
            "stderr": "" if succeeded else _extract_run_error(run),
            "runId": run["id"],
        }
    workspace = _workspace_from_config(cfg)
    target_path = Path(target_config_path).expanduser()
    resolved_target = sync_files.root_checked(str(target_path.resolve()))
    selected_names = skills if skills is not None else _target_filter_for(cfg, target_config_path)
    selected_skills = _select_source_skills(workspace, selected_names or None)

    if not selected_skills:
        if selected_names:
            reason = f"no matching skills in workspace: {', '.join(sorted(selected_names))}"
        else:
            reason = "workspace has no skills"
        return {
            "success": True,
            "stdout": f"No skills to sync ({reason})",
            "stderr": "",
            "syncedCount": 0,
        }

    if dry_run:
        return {
            "success": True,
            "stdout": "\n".join(f"Would sync {item['name']} -> {target_path}" for item in selected_skills),
            "stderr": "",
            "syncedCount": 0,
        }

    copied = 0
    for item in selected_skills:
        source_dir = workspace / item["path"]
        snapshot, bundle, digest = sync_files.make_bundle(source_dir)
        sync_files.install({
            "path": str(resolved_target),
            "name": item["name"],
            "bundle": bundle,
            "bundleDigest": digest,
            "sourceDigest": snapshot["digest"],
            "force": True,
            "workspaceId": str(workspace),
            "runId": str(uuid.uuid4()),
        })
        copied += 1

    return {
        "success": True,
        "stdout": f"Synced {copied} skill(s) to {target_path}",
        "stderr": "",
        "syncedCount": copied,
    }


def get_skill_presence(skill: str) -> dict:
    """Return target presence map for a skill."""
    cfg = load_config()
    workspace = _workspace_from_config(cfg)
    item = get_skill(workspace, skill)
    if not item:
        raise ValueError(f"Unknown skill: {skill}")
    targets = {
        target_path: _skill_status(workspace, target_path, item)
        for target_path in sync_targets.local_paths(cfg)
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
    target_exists = target_path.is_dir()
    if target_exists:
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
        "path": str(target_path),
        "exists": target_exists,
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


# ── agent dir discovery ────────────────────────────────────────────────────


_AGENT_CONVENTIONS: list[tuple[str, str]] = agent_catalog.project_agent_conventions()


def discover_agent_dirs(root_path: str) -> list[dict]:
    """Scan a project directory for built-in agent skill directories."""
    return agent_catalog.discover_project_agent_dirs(root_path)


def list_builtin_agents(
    *,
    include_undetected: bool = True,
    include_legacy: bool = False,
    cfg: SkillregConfig | None = None,
) -> dict:
    """Return built-in agent catalog enriched with local detection and config state."""
    cfg = cfg or load_config()
    configured_paths = {
        str(Path(r["path"]).expanduser().absolute())
        for r in sync_targets.configured_target_records(cfg)
        if r["transport"] == "local"
    }
    agents = []
    detected_count = 0
    active_count = 0
    for item in agent_catalog.detect_home_agents(
        include_undetected=include_undetected,
        include_legacy=include_legacy,
    ):
        canonical = str(Path(item["path"]).expanduser().absolute())
        configured = any(sync_targets._local_path_matches(path, canonical) for path in configured_paths)
        enabled = sync_targets._is_builtin_enabled(cfg, item["id"])
        active = configured or enabled
        if item["detected"]:
            detected_count += 1
        if active:
            active_count += 1
        agents.append({
            **item,
            "configured": configured,
            "enabled": enabled,
            "active": active,
            "added": active,
        })
    return {
        "agents": agents,
        "detectedCount": detected_count,
        "onboarding": cfg.agent_onboarding,
        "hasTargets": bool(configured_paths or active_count),
        "activeCount": active_count,
        "totalCount": len(agents),
    }


def discover_home_agent_dirs(
    *,
    include_undetected: bool = False,
    include_legacy: bool = False,
) -> list[dict]:
    """Auto-discover built-in agent dirs under ~/."""
    return list_builtin_agents(
        include_undetected=include_undetected,
        include_legacy=include_legacy,
    )["agents"]


def set_builtin_agent_enabled(agent_id: str, enabled: bool) -> dict:
    """Enable or hide a built-in auto-detected agent target."""
    return sync_targets.set_builtin_agent_enabled(agent_id, enabled)


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
    matched = [item for item in items if item["name"] in skill_set]
    if len(matched) < len(skill_set):
        items = get_all(workspace, force=True)["skills"]
        matched = [item for item in items if item["name"] in skill_set]
    return matched


def _skill_status(workspace: Path, target: str, item: dict) -> str:
    source_dir = workspace / item["path"]
    target_dir = Path(target).expanduser() / item["name"]
    if not target_dir.exists():
        return "missing"
    return "synced" if _dirs_equal(source_dir, target_dir) else "modified"


def _selected_targets(cfg: SkillregConfig, target: str | None) -> list[str]:
    records = [
        r for r in sync_targets.target_records(cfg, include_builtin=True)
        if r["transport"] == "local"
    ]
    targets = [r["path"] for r in records]
    if not target:
        return list(targets)
    try:
        resolved_path = _resolve_config_target(cfg, target)
        if resolved_path is not None:
            return [resolved_path]
    except ValueError:
        pass
    resolved = Path(target).expanduser()
    matched = [
        r["path"]
        for r in records
        if r["id"] == target
        or r["name"] == target
        or r["path"] == target
        or Path(r["path"]).expanduser() == resolved
        or _target_display_name(Path(r["path"])) == target
    ]
    return list(dict.fromkeys(matched)) or [target]


def _resolve_config_target(cfg: SkillregConfig, target: str) -> str | None:
    try:
        record = sync_targets.resolve_target(target, cfg=cfg)
    except sync_files.SyncError as exc:
        if exc.code == "not-found":
            return None
        raise
    except ValueError:
        return None
    if record["transport"] != "local":
        raise sync_files.SyncError("Use SSH preview and runs for remote targets", "invalid")
    return record["path"]


def _target_filter_for(cfg: SkillregConfig, target: str) -> list[str]:
    try:
        record = sync_targets.resolve_target(target, cfg=cfg)
        if record.get("skills"):
            return list(record["skills"])
    except ValueError:
        pass
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


def _is_ignored_entry_name(name: str, *, is_dir: bool = False) -> bool:
    if name in sync_files.IGNORED or name.startswith("._"):
        return True
    if not is_dir and name.endswith(".pyc"):
        return True
    return False


def _dirs_equal(source: Path, target: Path) -> bool:
    if not source.is_dir() or not target.is_dir():
        return False
    ignore_names = set(sync_files.IGNORED)
    for directory in (source, target):
        try:
            for entry in directory.iterdir():
                if _is_ignored_entry_name(entry.name, is_dir=entry.is_dir()):
                    ignore_names.add(entry.name)
        except OSError:
            return False
    comparison = filecmp.dircmp(source, target, ignore=list(ignore_names))
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
        if file_path.is_symlink() or not file_path.is_file():
            continue
        rel_parts = file_path.relative_to(root).parts
        if any(_is_ignored_entry_name(part, is_dir=idx < len(rel_parts) - 1) for idx, part in enumerate(rel_parts)):
            continue
        rel_path = "/".join(rel_parts)
        try:
            result[rel_path] = file_path.read_bytes()
        except OSError:
            continue
    return result


def _target_name(path: Path) -> str:
    return path.name or str(path)


def _target_display_name(path: Path) -> str:
    matched = agent_catalog.match_agent_for_path(path)
    if matched is not None:
        return matched.id
    resolved = path.expanduser()
    normalized = [part for part in resolved.parts if part not in ("/", "")]
    if len(normalized) >= 2 and normalized[-1] == "skills":
        parent = normalized[-2]
        if parent.startswith(".") and len(parent) > 1:
            return parent[1:]
        return parent
    return _target_name(resolved)
