"""Stable install target identities with built-in agent and local-path support."""

from __future__ import annotations

import uuid
from pathlib import Path, PurePosixPath
from threading import RLock

from ..config import load_config, save_config
from . import agent_catalog
from .sync_files import SyncError

_LOCK = RLock()

_STORED_RECORD_KEYS = (
    "id",
    "name",
    "path",
    "transport",
    "connectionId",
    "scope",
    "agentKind",
    "projectRoot",
    "skills",
)


def _canonical_local_path(value: str) -> str:
    return str(Path(value).expanduser().absolute())


def _storable_record(record: dict) -> dict:
    return {key: record.get(key) for key in _STORED_RECORD_KEYS}


def display_name(path: str) -> str:
    matched = agent_catalog.match_agent_for_path(path)
    if matched is not None:
        return matched.id
    resolved = Path(path).expanduser()
    parts = [p for p in resolved.parts if p not in ("/", "\\", "")]
    if len(parts) >= 2 and parts[-1] == "skills":
        parent = parts[-2]
        if parent.startswith(".") and len(parent) > 1:
            return parent[1:]
        return parent
    return resolved.name or str(resolved)


def _local_path_matches(record_path: str, identifier: str) -> bool:
    left = Path(record_path).expanduser()
    right = Path(identifier).expanduser()
    if left == right:
        return True
    if left.is_absolute() and right.is_absolute():
        try:
            return left.resolve() == right.resolve()
        except OSError:
            return False
    return False


def _is_builtin_enabled(cfg, agent_id: str) -> bool:
    entry = cfg.agents.get(agent_id)
    if isinstance(entry, dict) and entry.get("enabled") is False:
        return False
    return True


def configured_target_records(cfg=None) -> list[dict]:
    """Return targets explicitly stored in ``config.json``."""
    cfg = cfg or load_config()
    records = []
    for value in cfg.targets:
        if isinstance(value, str):
            canonical = _canonical_local_path(value)
            matched = agent_catalog.match_agent_for_path(value)
            record = {
                "id": str(
                    uuid.uuid5(uuid.NAMESPACE_URL, "skillreg:local:" + canonical)
                ),
                "name": display_name(value),
                "path": value,
                "transport": "local",
                "connectionId": None,
                "scope": "global",
                "agentKind": matched.id if matched else None,
                "projectRoot": None,
            }
        else:
            record = dict(value)
            if record.get("transport", "local") == "local" and not record.get("agentKind"):
                matched = agent_catalog.match_agent_for_path(record["path"])
                if matched:
                    record["agentKind"] = matched.id
        record["skills"] = list(
            record.get(
                "skills",
                cfg.target_skill_filters.get(
                    record["path"], cfg.target_skill_filters.get(record["name"], [])
                ),
            )
        )
        record["builtin"] = False
        record["source"] = "custom"
        records.append(record)
    return records


def builtin_target_records(cfg=None, *, include_disabled: bool = False) -> list[dict]:
    """Return auto-detected built-in agent targets not already overridden in config."""
    cfg = cfg or load_config()
    configured_local = {
        _canonical_local_path(r["path"])
        for r in configured_target_records(cfg)
        if r["transport"] == "local"
    }
    records = []
    for item in agent_catalog.detect_home_agents(include_undetected=False):
        canonical = _canonical_local_path(item["path"])
        if canonical in configured_local or any(
            _local_path_matches(cp, canonical) for cp in configured_local
        ):
            continue
        enabled = _is_builtin_enabled(cfg, item["id"])
        if not enabled and not include_disabled:
            continue
        skills = list(
            cfg.target_skill_filters.get(
                canonical,
                cfg.target_skill_filters.get(
                    item["id"],
                    cfg.target_skill_filters.get(item["name"], []),
                ),
            )
        )
        records.append(
            {
                "id": item["targetId"],
                "name": item["name"],
                "path": canonical,
                "transport": "local",
                "connectionId": None,
                "scope": "global",
                "agentKind": item["id"],
                "projectRoot": None,
                "skills": skills,
                "builtin": True,
                "source": "builtin",
                "detectedBy": item["detectedBy"],
                "exists": item["exists"],
                "shared": item["shared"],
                "readsShared": item["readsShared"],
                "relPath": item["rel_path"],
                "enabled": enabled,
            }
        )
    return records


def target_records(cfg=None, *, include_builtin: bool = True) -> list[dict]:
    """Return configured targets (first) merged with auto-detected built-in targets."""
    cfg = cfg or load_config()
    configured = configured_target_records(cfg)
    if not include_builtin:
        return configured
    return configured + builtin_target_records(cfg)


def local_paths(cfg=None, *, include_builtin: bool = True) -> list[str]:
    return [
        r["path"]
        for r in target_records(cfg, include_builtin=include_builtin)
        if r["transport"] == "local"
    ]


def _match_in_records(records: list[dict], identifier: str, *, match_agent: bool = False) -> dict | None:
    for record in records:
        if record["id"] == identifier:
            return record

    ident_lower = identifier.strip().lower()
    spec = agent_catalog.get_agent_spec(identifier) if match_agent else None

    matches = []
    for record in records:
        if record["name"] == identifier:
            matches.append(record)
            continue
        if (
            record["transport"] == "local"
            and _local_path_matches(record["path"], identifier)
        ):
            matches.append(record)
            continue
        if match_agent:
            agent_kind = (record.get("agentKind") or "").lower()
            if (
                record["name"].lower() == ident_lower
                or (agent_kind and agent_kind == ident_lower)
                or (spec is not None and agent_kind == spec.id)
            ):
                matches.append(record)

    if len(matches) == 1:
        return matches[0]
    if matches:
        raise SyncError("Target name is ambiguous; use its ID", "ambiguous-target")
    return None


def resolve_target(
    identifier: str,
    *,
    allow_path: bool = False,
    cfg=None,
    include_builtin: bool = True,
) -> dict:
    cfg = cfg or load_config()
    configured = configured_target_records(cfg)
    matched = _match_in_records(configured, identifier, match_agent=False)
    if matched is not None:
        return matched

    if include_builtin:
        builtins = builtin_target_records(cfg)
        matched = _match_in_records(builtins, identifier, match_agent=True)
        if matched is not None:
            return matched

    if allow_path:
        path = Path(identifier).expanduser()
        if path.is_absolute() or "/" in identifier:
            return {
                "id": str(
                    uuid.uuid5(
                        uuid.NAMESPACE_URL, "skillreg:local:" + str(path.absolute())
                    )
                ),
                "name": display_name(identifier),
                "path": str(path.absolute()),
                "transport": "local",
                "connectionId": None,
                "skills": [],
                "builtin": False,
                "source": "custom",
            }
    raise SyncError("Target not found: " + identifier, "not-found")


def add_target(
    name: str,
    path: str,
    connection_id: str | None = None,
    scope: str = "global",
    agent_kind: str | None = None,
    project_root: str | None = None,
    skills: list[str] | None = None,
) -> dict:
    from .ssh_connections import get_connection

    if not name.strip() or scope not in {"global", "project"}:
        raise SyncError("Provide a target name and valid scope")
    if (
        not path
        or any(c in path for c in "\x00\n\r")
        or ".." in PurePosixPath(path).parts
    ):
        raise SyncError("Invalid target path")
    if connection_id:
        connection_id = get_connection(connection_id)["id"]
        if not path.startswith(("/", "~/")):
            raise SyncError("Remote path must be absolute or start with ~/")
    else:
        expanded = Path(path).expanduser()
        if expanded.is_symlink():
            path = str(expanded.absolute())
        else:
            abs_path = expanded.absolute()
            path = str(abs_path.parent.resolve() / abs_path.name)
        if not agent_kind:
            matched_agent = agent_catalog.match_agent_for_path(path)
            if matched_agent:
                agent_kind = matched_agent.id
    with _LOCK:
        cfg = load_config()
        records = configured_target_records(cfg)
        if any(
            r["connectionId"] == connection_id and r["path"] == path for r in records
        ):
            raise SyncError("Target already exists", "conflict")
        record = {
            "id": str(uuid.uuid4()),
            "name": name.strip(),
            "path": path,
            "transport": "ssh" if connection_id else "local",
            "connectionId": connection_id,
            "scope": scope,
            "agentKind": agent_kind,
            "projectRoot": project_root,
            "skills": list(dict.fromkeys(skills or [])),
        }
        if agent_kind and isinstance(cfg.agents.get(agent_kind), dict):
            if cfg.agents[agent_kind].get("enabled") is False:
                cfg.agents[agent_kind] = {**cfg.agents[agent_kind], "enabled": True}
        cfg.targets = [_storable_record(r) for r in records] + [record]
        save_config(cfg)
        return {**record, "builtin": False, "source": "custom"}


def update_target(identifier: str, **changes) -> dict:
    with _LOCK:
        cfg = load_config()
        selected = resolve_target(identifier, cfg=cfg)
        allowed = {
            key: value for key, value in changes.items() if key in {"name", "skills"}
        }
        if "name" in allowed and not allowed["name"].strip():
            raise SyncError("Target name cannot be empty")

        configured = configured_target_records(cfg)
        if selected.get("builtin"):
            if "skills" in allowed:
                cfg.target_skill_filters[selected["path"]] = list(allowed["skills"])
            if "name" in allowed:
                promoted = {
                    **_storable_record(selected),
                    "name": allowed["name"].strip(),
                    "skills": list(allowed.get("skills", selected.get("skills", []))),
                }
                cfg.targets = [_storable_record(r) for r in configured] + [promoted]
                save_config(cfg)
                return {**promoted, "builtin": False, "source": "custom"}
            selected.update(allowed)
            save_config(cfg)
            return selected

        selected.update(allowed)
        cfg.targets = [
            _storable_record(selected if r["id"] == selected["id"] else r)
            for r in configured
        ]
        if "skills" in changes and selected["transport"] == "local":
            cfg.target_skill_filters[selected["path"]] = list(changes["skills"])
        save_config(cfg)
        return selected


def remove_target(identifier: str) -> None:
    with _LOCK:
        cfg = load_config()
        selected = resolve_target(identifier, cfg=cfg)
        if selected.get("builtin"):
            agent_id = selected.get("agentKind")
            if not agent_id:
                raise SyncError("Built-in target has no agent identifier")
            existing = cfg.agents.get(agent_id)
            next_entry = dict(existing) if isinstance(existing, dict) else {}
            next_entry["enabled"] = False
            cfg.agents[agent_id] = next_entry
            save_config(cfg)
            return
        configured = configured_target_records(cfg)
        cfg.targets = [
            _storable_record(r) for r in configured if r["id"] != selected["id"]
        ]
        cfg.target_skill_filters.pop(selected["path"], None)
        save_config(cfg)


def set_builtin_agent_enabled(agent_id: str, enabled: bool) -> dict:
    """Enable or hide a built-in auto-detected agent target in config."""
    spec = agent_catalog.get_agent_spec(agent_id)
    if spec is None:
        raise SyncError("Unknown built-in agent: " + agent_id, "not-found")
    with _LOCK:
        cfg = load_config()
        existing = cfg.agents.get(spec.id)
        entry = dict(existing) if isinstance(existing, dict) else {}
        entry["enabled"] = bool(enabled)
        cfg.agents[spec.id] = entry
        save_config(cfg)
    return {"id": spec.id, "name": spec.name, "enabled": bool(enabled)}
