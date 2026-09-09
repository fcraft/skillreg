"""Persistent sync previews, execution receipts and observation snapshots"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from threading import Thread

from .. import config
from . import ssh_connections, sync_files, sync_targets
from .skill_registry import get_all
from .sync_files import SyncError

TERMINAL = {"succeeded", "partially-succeeded", "failed", "cancelled"}


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def database_path() -> Path:
    return config.CONFIG_FILE.parent / "state.db"


@contextmanager
def database(path: Path | None = None):
    path = path or database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=15)
    try:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS previews (id TEXT PRIMARY KEY, expires REAL, consumed INTEGER DEFAULT 0, payload TEXT)"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, created TEXT, payload TEXT)"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS observations (key TEXT PRIMARY KEY, payload TEXT)"
        )
        yield connection
        connection.commit()
    finally:
        connection.close()


def _error(exc: Exception) -> dict:
    return {
        "code": getattr(exc, "code", "io-error"),
        "message": str(exc),
        "retryable": getattr(exc, "retryable", False),
    }


def workspace() -> Path:
    value = config.load_config().workspace_path
    if not value:
        raise SyncError("Workspace not configured", "workspace-missing")
    root = Path(value).expanduser().resolve()
    if not (root / "skills").is_dir():
        raise SyncError("Workspace is unavailable", "workspace-missing")
    return root


def _revision(root: Path) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=5,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _diff(source: dict, target: dict) -> list[dict]:
    files = []
    for path in sorted(set(source) | set(target)):
        change = (
            "added"
            if path not in target
            else "deleted"
            if path not in source
            else "unchanged"
            if source[path] == target[path]
            else "modified"
        )
        files.append({"path": path, "change": change})
    return files


def preview(
    target_ids: list[str],
    skills: list[str] | None = None,
    *,
    target_skills: dict[str, list[str]] | None = None,
) -> dict:
    if not target_ids:
        raise SyncError("Select at least one target")
    if skills is not None and not skills:
        raise SyncError("Select at least one skill")
    root = workspace()
    catalog = {s["name"]: s for s in get_all(root, force=True)["skills"]}
    if skills and set(skills) - catalog.keys():
        raise SyncError(
            "Skills not found: " + ", ".join(sorted(set(skills) - catalog.keys()))
        )
    sources = {}
    targets = []
    for identifier in dict.fromkeys(target_ids):
        target = sync_targets.resolve_target(identifier)
        selected = list(
            dict.fromkeys(
                target_skills[target["id"]]
                if target_skills is not None
                else skills
                if skills is not None
                else target.get("skills") or list(catalog)
            )
        )
        if set(selected) - catalog.keys():
            raise SyncError(
                "Configured skill no longer exists; update target selection"
            )
        rows = []
        for name in selected:
            sync_files.name_checked(name)
            if name not in sources:
                source = root / catalog[name]["path"]
                if not source.resolve().is_relative_to(root):
                    raise SyncError(
                        "Skill source is outside the workspace", "unsafe-path"
                    )
                snapshot, bundle, digest = sync_files.make_bundle(source)
                sources[name] = {
                    "path": catalog[name]["path"],
                    "snapshot": snapshot,
                    "bundle": bundle,
                    "bundleDigest": digest,
                }
        connection = (
            ssh_connections.get_connection(target["connectionId"])
            if target["transport"] == "ssh"
            else None
        )
        item = {
            "target": target,
            "connection": connection,
            "skills": rows,
            "selectedSkills": selected,
            "error": None,
            "observedAt": now(),
        }
        try:
            observed = ssh_connections.call(
                connection,
                {"operation": "inspect", "path": target["path"], "names": selected},
            )
            target["path"] = observed["path"]
            if not observed["writable"]:
                raise SyncError("Target directory is not writable", "permission-denied")
            for name in selected:
                actual = observed["skills"][name]
                expected = sources[name]["snapshot"]
                status = (
                    "missing"
                    if not actual["exists"]
                    else "synced"
                    if actual["digest"] == expected["digest"]
                    else "modified"
                )
                rows.append(
                    {
                        "name": name,
                        "status": status,
                        "sourceDigest": expected["digest"],
                        "targetDigest": actual["digest"],
                        "files": _diff(expected["files"], actual["files"]),
                    }
                )
        except Exception as exc:
            item["error"] = _error(exc)
        targets.append(item)
    record = {
        "id": str(uuid.uuid4()),
        "createdAt": now(),
        "workspace": str(root),
        "workspaceId": hashlib.sha256(str(root).encode()).hexdigest(),
        "revision": _revision(root),
        "sources": sources,
        "targets": targets,
    }
    with database() as db:
        db.execute("DELETE FROM previews WHERE expires < ?", (time.time(),))
        db.execute(
            "INSERT INTO previews(id, expires, payload) VALUES (?, ?, ?)",
            (record["id"], time.time() + 900, json.dumps(record)),
        )
        for target in targets:
            _save_observation(db, record, target)
    return public_preview(record)


def public_preview(record: dict) -> dict:
    return {
        "id": record["id"],
        "createdAt": record["createdAt"],
        "workspace": record["workspace"],
        "revision": record["revision"],
        "expiresInSeconds": 900,
        "targets": [
            {k: v for k, v in t.items() if k != "connection"} for t in record["targets"]
        ],
        "requiresOverwrite": any(
            s["status"] == "modified" for t in record["targets"] for s in t["skills"]
        ),
    }


def _save_observation(db, record: dict, target: dict) -> None:
    key = record["workspaceId"] + ":" + target["target"]["id"]
    value = {
        "targetId": target["target"]["id"],
        "workspace": record["workspace"],
        "observedAt": target["observedAt"],
        "error": target.get("error"),
        "skills": target["skills"],
    }
    db.execute(
        "INSERT OR REPLACE INTO observations(key, payload) VALUES (?, ?)",
        (key, json.dumps(value)),
    )


def observations() -> list[dict]:
    current = str(workspace())
    with database() as db:
        values = [
            json.loads(row[0]) for row in db.execute("SELECT payload FROM observations")
        ]
    return [value for value in values if value["workspace"] == current]


def create_run(preview_id: str, force: bool = False, background: bool = True) -> dict:
    path = database_path()
    with database(path) as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT payload, expires, consumed FROM previews WHERE id = ?",
            (preview_id,),
        ).fetchone()
        if row is None or row[1] < time.time() or row[2]:
            raise SyncError(
                "Preview expired or already used; preview again", "preview-expired"
            )
        snapshot = json.loads(row[0])
        if snapshot["workspace"] != str(workspace()):
            raise SyncError("Workspace changed; preview again", "source-changed")
        for name, source in snapshot["sources"].items():
            if (
                sync_files.tree_snapshot(Path(snapshot["workspace"]) / source["path"])[
                    "digest"
                ]
                != source["snapshot"]["digest"]
            ):
                raise SyncError(
                    "Source changed since preview: " + name, "source-changed"
                )
        if public_preview(snapshot)["requiresOverwrite"] and not force:
            raise SyncError(
                "Preview contains modified skills; confirm overwrite", "conflict"
            )
        if not any(t["skills"] and not t["error"] for t in snapshot["targets"]):
            raise SyncError("No reachable targets with selected skills", "no-targets")
        run = {
            "id": str(uuid.uuid4()),
            "previewId": preview_id,
            "workspace": snapshot["workspace"],
            "revision": snapshot["revision"],
            "createdAt": now(),
            "finishedAt": None,
            "state": "queued",
            "step": "queued",
            "workerPid": os.getpid(),
            "force": force,
            "progress": {
                "completed": 0,
                "total": sum(len(t["skills"]) for t in snapshot["targets"]),
            },
            "results": [
                {
                    "target": t["target"],
                    "state": "failed" if t["error"] else "queued",
                    "error": t["error"],
                    "skills": [
                        {
                            "name": s["name"],
                            "sourceDigest": s["sourceDigest"],
                            "state": "queued",
                        }
                        for s in t["skills"]
                    ],
                }
                for t in snapshot["targets"]
            ],
        }
        for result, planned in zip(run["results"], snapshot["targets"]):
            result["selectedSkills"] = planned["selectedSkills"]
        db.execute("UPDATE previews SET consumed = 1 WHERE id = ?", (preview_id,))
        db.execute(
            "INSERT INTO runs(id, created, payload) VALUES (?, ?, ?)",
            (run["id"], run["createdAt"], json.dumps(run)),
        )
    if background:
        Thread(target=_execute, args=(path, snapshot, run), daemon=True).start()
        return get_run(run["id"], path)
    _execute(path, snapshot, run)
    return get_run(run["id"], path)


def _save_run(path: Path, run: dict) -> None:
    with database(path) as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT payload FROM runs WHERE id = ?", (run["id"],)
        ).fetchone()
        if row and json.loads(row[0]).get("cancelRequested"):
            run["cancelRequested"] = True
        db.execute(
            "UPDATE runs SET payload = ? WHERE id = ?", (json.dumps(run), run["id"])
        )


def _cancel_requested(path: Path, identifier: str) -> bool:
    with database(path) as db:
        row = db.execute(
            "SELECT payload FROM runs WHERE id = ?", (identifier,)
        ).fetchone()
    return bool(row and json.loads(row[0]).get("cancelRequested"))


def _execute(path: Path, snapshot: dict, run: dict) -> None:
    run.update(state="running", step="installing")
    _save_run(path, run)
    try:
        for planned, target_result in zip(snapshot["targets"], run["results"]):
            if planned["error"]:
                continue
            target_result["state"] = "running"
            for skill, result in zip(planned["skills"], target_result["skills"]):
                if _cancel_requested(path, run["id"]):
                    run["cancelRequested"] = True
                if run.get("cancelRequested"):
                    result["state"] = "cancelled"
                    continue
                run.update(
                    currentTarget=planned["target"]["id"], currentSkill=skill["name"]
                )
                result["state"] = "running"
                _save_run(path, run)
                source = snapshot["sources"][skill["name"]]
                try:
                    outcome = ssh_connections.call(
                        planned["connection"],
                        {
                            "operation": "install",
                            "path": planned["target"]["path"],
                            "name": skill["name"],
                            "bundle": source["bundle"],
                            "bundleDigest": source["bundleDigest"],
                            "sourceDigest": skill["sourceDigest"],
                            "expectedDigest": skill["targetDigest"],
                            "force": run["force"],
                            "workspaceId": snapshot["workspaceId"],
                            "runId": run["id"],
                        },
                    )
                    result.update(state="succeeded", **outcome)
                except Exception as exc:
                    result.update(state="failed", error=_error(exc))
                run["progress"]["completed"] += 1
                _save_run(path, run)
            target_result["state"] = _aggregate(
                [s["state"] for s in target_result["skills"]]
            )
            run["step"] = "verifying"
            try:
                names = [s["name"] for s in planned["skills"]]
                observed = ssh_connections.call(
                    planned["connection"],
                    {
                        "operation": "inspect",
                        "path": planned["target"]["path"],
                        "names": names,
                    },
                )
                rows = []
                for skill, result in zip(planned["skills"], target_result["skills"]):
                    actual = observed["skills"][skill["name"]]
                    status = (
                        "missing"
                        if not actual["exists"]
                        else "synced"
                        if actual["digest"] == skill["sourceDigest"]
                        else "modified"
                    )
                    rows.append(
                        {
                            "name": skill["name"],
                            "status": status,
                            "sourceDigest": skill["sourceDigest"],
                            "targetDigest": actual["digest"],
                        }
                    )
                    if result["state"] == "succeeded" and status != "synced":
                        result.update(
                            state="failed",
                            status=status,
                            error={
                                "code": "verification-failed",
                                "message": "Target changed after installation",
                                "retryable": True,
                            },
                        )
                observation = {
                    "target": planned["target"],
                    "skills": rows,
                    "observedAt": now(),
                }
            except Exception as exc:
                observation = {
                    "target": planned["target"],
                    "skills": [],
                    "observedAt": now(),
                    "error": _error(exc),
                }
                target_result["error"] = _error(exc)
                for result in target_result["skills"]:
                    if result["state"] == "succeeded":
                        result.update(state="failed", error=_error(exc))
            with database(path) as db:
                _save_observation(db, snapshot, observation)
            target_result["state"] = _aggregate(
                [s["state"] for s in target_result["skills"]]
            )
            run["step"] = "installing"
        run["state"] = _aggregate([r["state"] for r in run["results"]])
    except Exception as exc:
        run.update(state="failed", error=_error(exc))
    finally:
        run.update(step="finished", finishedAt=now())
        _save_run(path, run)


def _aggregate(states: list[str]) -> str:
    if states and all(s == "succeeded" for s in states):
        return "succeeded"
    if "succeeded" in states or "partially-succeeded" in states:
        return "partially-succeeded"
    return "cancelled" if "cancelled" in states else "failed"


def get_run(identifier: str, path: Path | None = None) -> dict:
    with database(path) as db:
        row = db.execute(
            "SELECT payload FROM runs WHERE id = ?", (identifier,)
        ).fetchone()
        if not row:
            raise SyncError("Sync run not found", "not-found")
        run = json.loads(row[0])
        if run["state"] not in TERMINAL:
            try:
                os.kill(run["workerPid"], 0)
            except ProcessLookupError:
                run.update(
                    state="failed",
                    step="interrupted",
                    finishedAt=now(),
                    error={
                        "code": "interrupted",
                        "message": "Sync process exited; refresh targets before retrying",
                        "retryable": True,
                    },
                )
                db.execute(
                    "UPDATE runs SET payload = ? WHERE id = ?",
                    (json.dumps(run), identifier),
                )
    return run


def history(limit: int = 50) -> list[dict]:
    with database() as db:
        ids = [
            row[0]
            for row in db.execute(
                "SELECT id FROM runs ORDER BY created DESC, rowid DESC LIMIT ?",
                (min(max(limit, 1), 200),),
            )
        ]
    return [get_run(identifier) for identifier in ids]


def cancel_run(identifier: str) -> dict:
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT payload FROM runs WHERE id = ?", (identifier,)
        ).fetchone()
        if not row:
            raise SyncError("Sync run not found", "not-found")
        run = json.loads(row[0])
        if run["state"] in TERMINAL:
            return run
        run["cancelRequested"] = True
        db.execute(
            "UPDATE runs SET payload = ? WHERE id = ?", (json.dumps(run), identifier)
        )
    return run


def retry_preview(identifier: str) -> dict:
    run = get_run(identifier)
    if run["state"] not in TERMINAL:
        raise SyncError("Run is still active", "conflict")
    if run["workspace"] != str(workspace()):
        raise SyncError(
            "Switch to the run's workspace before retrying", "source-changed"
        )
    targets = [r["target"]["id"] for r in run["results"] if r["state"] != "succeeded"]
    selections = {
        r["target"]["id"]: r["selectedSkills"]
        for r in run["results"]
        if r["state"] != "succeeded"
    }
    if not targets:
        raise SyncError("No failed targets to retry")
    return preview(targets, target_skills=selections)
