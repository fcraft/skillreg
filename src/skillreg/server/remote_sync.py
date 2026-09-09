"""Connection, install target and sync run API"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..services import ssh_connections, sync_inventory, sync_runs, sync_targets
from ..services.sync_files import SyncError

router = APIRouter(prefix="/api", tags=["remote-sync"])


class ConnectionBody(BaseModel):
    name: str
    host: str
    user: str | None = None
    port: int | None = Field(None, ge=1, le=65535)
    identityFile: str | None = None


class TargetBody(BaseModel):
    name: str
    path: str
    connectionId: str | None = None
    scope: str = "global"
    agentKind: str | None = None
    projectRoot: str | None = None
    skills: list[str] | None = None


class TargetUpdateBody(BaseModel):
    name: str | None = None
    skills: list[str] | None = None


class PreviewBody(BaseModel):
    targetIds: list[str]
    skills: list[str] | None = None


class RunBody(BaseModel):
    previewId: str
    force: bool = False


def invoke(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except SyncError as exc:
        status = (
            404
            if exc.code == "not-found"
            else 409
            if exc.code
            in {"conflict", "preview-expired", "source-changed", "target-changed"}
            else 400
        )
        raise HTTPException(
            status, {"code": exc.code, "message": str(exc), "retryable": exc.retryable}
        ) from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(400, {"code": "invalid", "message": str(exc)}) from exc


@router.get("/connections")
def connections():
    return invoke(ssh_connections.list_connections)


@router.post("/connections")
def add_connection(body: ConnectionBody):
    return invoke(
        ssh_connections.save_connection,
        body.name,
        body.host,
        body.user,
        body.port,
        body.identityFile,
    )


@router.put("/connections/{identifier}")
def edit_connection(identifier: str, body: ConnectionBody):
    return invoke(
        ssh_connections.save_connection,
        body.name,
        body.host,
        body.user,
        body.port,
        body.identityFile,
        identifier,
    )


@router.delete("/connections/{identifier}")
def remove_connection(identifier: str):
    invoke(ssh_connections.remove_connection, identifier)
    return {"success": True}


@router.post("/connections/{identifier}/check")
def check_connection(identifier: str):
    return invoke(ssh_connections.check_connection, identifier)


@router.get("/connections/{identifier}/discover-targets")
def discover(identifier: str, root: str | None = None):
    return invoke(ssh_connections.discover, identifier, root)


@router.get("/targets")
def targets():
    return invoke(sync_targets.target_records)


@router.post("/targets")
def add_target(body: TargetBody):
    return invoke(
        sync_targets.add_target,
        body.name,
        body.path,
        body.connectionId,
        body.scope,
        body.agentKind,
        body.projectRoot,
        body.skills,
    )


@router.get("/targets/{identifier}/inventory")
def target_inventory(identifier: str):
    return invoke(sync_inventory.inspect_target, identifier)


@router.get("/targets/{identifier}/skills/{name}/document")
def target_skill_document(identifier: str, name: str):
    return invoke(sync_inventory.read_skill, identifier, name)


@router.put("/targets/{identifier}")
def edit_target(identifier: str, body: TargetUpdateBody):
    return invoke(
        sync_targets.update_target, identifier, **body.model_dump(exclude_none=True)
    )


@router.delete("/targets/{identifier}")
def remove_target(identifier: str):
    invoke(sync_targets.remove_target, identifier)
    return {"success": True}


@router.post("/sync/preview")
def preview(body: PreviewBody):
    return invoke(sync_runs.preview, body.targetIds, body.skills)


@router.get("/sync/observations")
def observations():
    return invoke(sync_runs.observations)


@router.post("/sync/runs")
def create_run(body: RunBody):
    return invoke(sync_runs.create_run, body.previewId, body.force)


@router.get("/sync/runs")
def runs(limit: int = Query(50, ge=1, le=200)):
    return invoke(sync_runs.history, limit)


@router.get("/sync/runs/{identifier}")
def run(identifier: str):
    return invoke(sync_runs.get_run, identifier)


@router.post("/sync/runs/{identifier}/cancel")
def cancel(identifier: str):
    return invoke(sync_runs.cancel_run, identifier)


@router.post("/sync/runs/{identifier}/retry")
def retry(identifier: str):
    return invoke(sync_runs.retry_preview, identifier)
