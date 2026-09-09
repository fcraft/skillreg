"""SSH connection configuration and transport"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from threading import RLock
import shlex

from .. import config
from . import sync_files
from .sync_files import SyncError

_LOCK = RLock()


def _path() -> Path:
    return config.CONFIG_FILE.parent / "connections.json"


def list_connections() -> list[dict]:
    path = _path()
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def get_connection(identifier: str) -> dict:
    matches = [
        c
        for c in list_connections()
        if c["id"] == identifier or c["name"] == identifier
    ]
    if len(matches) != 1:
        raise SyncError("Connection not found or name is ambiguous", "not-found")
    return matches[0]


def _save(records: list[dict]) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".connections-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(records, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def save_connection(
    name: str,
    host: str,
    user: str | None = None,
    port: int | None = None,
    identity_file: str | None = None,
    identifier: str | None = None,
) -> dict:
    if not name.strip() or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:\[\]-]*", host):
        raise SyncError("Provide a connection name and SSH host or config alias")
    if user and not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", user):
        raise SyncError("Invalid SSH user")
    if port is not None and not 1 <= port <= 65535:
        raise SyncError("SSH port must be between 1 and 65535")
    if identity_file and any(c in identity_file for c in "\x00\n\r"):
        raise SyncError("Invalid identity file path")
    with _LOCK:
        records = list_connections()
        if identifier:
            identifier = get_connection(identifier)["id"]
        if any(c["name"] == name.strip() and c["id"] != identifier for c in records):
            raise SyncError("Connection name already exists", "conflict")
        record = {
            "id": identifier or str(uuid.uuid4()),
            "name": name.strip(),
            "host": host,
            "user": user or None,
            "port": port,
            "identityFile": identity_file or None,
            "status": "unknown",
            "checkedAt": None,
        }
        records = [record if c["id"] == record["id"] else c for c in records]
        if not identifier:
            records.append(record)
        _save(records)
        return record


def remove_connection(identifier: str) -> None:
    from .sync_targets import target_records

    with _LOCK:
        connection = get_connection(identifier)
        if any(t.get("connectionId") == connection["id"] for t in target_records()):
            raise SyncError("Remove this connection's targets first", "conflict")
        _save([c for c in list_connections() if c["id"] != connection["id"]])


def ssh_arguments(connection: dict) -> list[str]:
    args = [
        "ssh",
        "-T",
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        "ConnectTimeout=10",
        "-o",
        "ServerAliveInterval=10",
        "-o",
        "ServerAliveCountMax=2",
        "-o",
        "ForwardAgent=no",
        "-o",
        "ClearAllForwardings=yes",
        "-o",
        "PermitLocalCommand=no",
    ]
    if connection.get("user"):
        args += ["-l", connection["user"]]
    if connection.get("port"):
        args += ["-p", str(connection["port"])]
    if connection.get("identityFile"):
        args += ["-i", str(Path(connection["identityFile"]).expanduser())]
    return args + [connection["host"]]


def call(connection: dict | None, request: dict, timeout: int = 120) -> dict:
    if connection is None:
        return sync_files.dispatch(request)
    code = Path(sync_files.__file__).read_text(encoding="utf-8")
    try:
        result = subprocess.run(
            ssh_arguments(connection) + ["python3 -c " + shlex.quote(code)],
            input=json.dumps(request),
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise SyncError(
            "SSH operation timed out; refresh target status before retrying",
            "timeout",
            True,
        ) from exc
    except OSError as exc:
        raise SyncError(
            "Cannot run the system SSH client: " + str(exc), "ssh-unavailable"
        ) from exc
    try:
        payload = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        error = (
            result.stderr.strip()[-2000:]
            or "Remote host did not return a sync response"
        )
        code = "offline"
        if (
            "REMOTE HOST IDENTIFICATION HAS CHANGED" in error
            or "Host key verification failed" in error
        ):
            code = (
                "host-key-changed" if "HAS CHANGED" in error else "host-key-untrusted"
            )
        elif "Permission denied" in error:
            code = "auth-failed"
        elif "python3" in error:
            code = "unsupported-platform"
        raise SyncError(error, code, code == "offline")
    if not payload.get("ok"):
        error = payload.get("error", {})
        raise SyncError(
            error.get("message", "Remote sync failed"),
            error.get("code", "remote-error"),
            error.get("retryable", False),
        )
    if result.returncode:
        raise SyncError(
            "SSH ended before confirming the result; refresh target status",
            "connection-lost",
            True,
        )
    return payload["result"]


def check_connection(identifier: str) -> dict:
    connection = get_connection(identifier)
    start = time.monotonic()
    observed = {"checkedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    try:
        details = call(connection, {"operation": "check"}, timeout=20)
        observed.update(
            status="online",
            details=details,
            error=None,
            latencyMs=round((time.monotonic() - start) * 1000),
        )
    except SyncError as exc:
        observed.update(status=exc.code, error=str(exc), details=None)
    with _LOCK:
        records = list_connections()
        for record in records:
            if record["id"] == connection["id"]:
                record.update(observed)
                connection = record
        _save(records)
    return connection


def discover(identifier: str, root: str | None = None) -> dict:
    return call(get_connection(identifier), {"operation": "discover", "root": root})
