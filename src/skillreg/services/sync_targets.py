"""Stable install target identities with legacy local-path compatibility"""

from __future__ import annotations

import uuid
from pathlib import Path, PurePosixPath
from threading import RLock

from ..config import load_config, save_config
from .sync_files import SyncError

_LOCK = RLock()


def display_name(path: str) -> str:
    parts = Path(path).parts
    return (
        parts[-2].lstrip(".")
        if len(parts) > 1 and parts[-1] == "skills"
        else Path(path).name
    )


def target_records(cfg=None) -> list[dict]:
    cfg = cfg or load_config()
    records = []
    for value in cfg.targets:
        if isinstance(value, str):
            canonical = str(Path(value).expanduser().absolute())
            record = {
                "id": str(
                    uuid.uuid5(uuid.NAMESPACE_URL, "skillreg:local:" + canonical)
                ),
                "name": display_name(value),
                "path": value,
                "transport": "local",
                "connectionId": None,
                "scope": "global",
                "agentKind": None,
                "projectRoot": None,
            }
        else:
            record = dict(value)
        record["skills"] = list(
            record.get(
                "skills",
                cfg.target_skill_filters.get(
                    record["path"], cfg.target_skill_filters.get(record["name"], [])
                ),
            )
        )
        records.append(record)
    return records


def local_paths(cfg=None) -> list[str]:
    return [r["path"] for r in target_records(cfg) if r["transport"] == "local"]


def resolve_target(identifier: str, *, allow_path: bool = False, cfg=None) -> dict:
    records = target_records(cfg)
    for record in records:
        if record["id"] == identifier:
            return record
    matches = [
        r
        for r in records
        if r["name"] == identifier
        or (
            r["transport"] == "local"
            and Path(r["path"]).expanduser() == Path(identifier).expanduser()
        )
    ]
    if len(matches) == 1:
        return matches[0]
    if matches:
        raise SyncError("Target name is ambiguous; use its ID", "ambiguous-target")
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
        path = str(Path(path).expanduser().absolute())
    with _LOCK:
        cfg = load_config()
        records = target_records(cfg)
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
        cfg.targets = records + [record]
        save_config(cfg)
        return record


def update_target(identifier: str, **changes) -> dict:
    with _LOCK:
        cfg = load_config()
        selected = resolve_target(identifier, cfg=cfg)
        allowed = {
            key: value for key, value in changes.items() if key in {"name", "skills"}
        }
        if "name" in allowed and not allowed["name"].strip():
            raise SyncError("Target name cannot be empty")
        selected.update(allowed)
        cfg.targets = [
            selected if r["id"] == selected["id"] else r for r in target_records(cfg)
        ]
        if "skills" in changes and selected["transport"] == "local":
            cfg.target_skill_filters[selected["path"]] = list(changes["skills"])
        save_config(cfg)
        return selected


def remove_target(identifier: str) -> None:
    with _LOCK:
        cfg = load_config()
        selected = resolve_target(identifier, cfg=cfg)
        cfg.targets = [r for r in target_records(cfg) if r["id"] != selected["id"]]
        cfg.target_skill_filters.pop(selected["path"], None)
        save_config(cfg)
