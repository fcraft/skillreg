"""Read-only, on-demand inventory for a saved installation target"""

from __future__ import annotations

from datetime import datetime, timezone

from . import ssh_connections, sync_targets
from .sync_files import name_checked


def _call(identifier: str, operation: str, **values) -> dict:
    target = sync_targets.resolve_target(identifier)
    connection = (
        ssh_connections.get_connection(target["connectionId"])
        if target["transport"] == "ssh"
        else None
    )
    result = ssh_connections.call(
        connection, {"operation": operation, "path": target["path"], **values}
    )
    return {
        **result,
        "targetId": target["id"],
        "observedAt": datetime.now(timezone.utc).isoformat(),
    }


def inspect_target(identifier: str) -> dict:
    return _call(identifier, "inventory")


def read_skill(identifier: str, name: str) -> dict:
    return _call(identifier, "read-skill", name=name_checked(name))
