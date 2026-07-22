"""Managed NPM source API."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import load_config
from ..services.source_manager import SourceManager


router = APIRouter(prefix="/api/sources", tags=["sources"])


class NpmPreviewBody(BaseModel):
    package: str
    registry: str = "https://registry.npmjs.org/"
    versionSpec: str = "latest"


class NpmImportBody(BaseModel):
    token: str
    mode: str
    selectedSkills: list[str]
    targetPath: str | None = None
    force: bool = False
    remote: str | None = None
    branch: str | None = None


class UpdatePreviewBody(BaseModel):
    versionSpec: str | None = None


class UpdateBody(BaseModel):
    token: str
    force: bool = False
    dryRun: bool = False


def _manager() -> SourceManager:
    config = load_config()
    if not config.workspace_path:
        raise HTTPException(400, "Workspace not configured")
    try:
        return SourceManager(Path(config.workspace_path))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


def _call(operation):
    try:
        return {"success": True, "data": operation()}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/npm/preview")
def preview_npm(body: NpmPreviewBody):
    manager = _manager()
    return _call(lambda: manager.preview_npm(body.package, body.registry, body.versionSpec))


@router.post("/npm/import")
def import_npm(body: NpmImportBody):
    manager = _manager()
    return _call(lambda: manager.import_npm(
        body.token,
        body.mode,
        body.selectedSkills,
        target_path=body.targetPath,
        force=body.force,
        remote=body.remote,
        branch=body.branch,
    ))


@router.get("")
def list_sources():
    manager = _manager()
    return _call(manager.list_sources)


@router.post("/{source_id}/check")
def check_source(source_id: str):
    manager = _manager()
    return _call(lambda: manager.check(source_id))


@router.post("/{source_id}/update-preview")
def preview_update(source_id: str, body: UpdatePreviewBody = UpdatePreviewBody()):
    manager = _manager()
    return _call(lambda: manager.update_preview(source_id, body.versionSpec))


@router.post("/{source_id}/update")
def update_source(source_id: str, body: UpdateBody):
    manager = _manager()
    return _call(lambda: manager.update(source_id, body.token, force=body.force, dry_run=body.dryRun))
