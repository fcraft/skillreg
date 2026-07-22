"""Workspace pointer management routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services import importer
from ..config import load_config, save_config
from ..services.directory_picker import (
    DirectoryPickerUnavailableError,
    select_directory,
)
from ..services.self_skill import init_self_skill

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


class SwitchWorkspaceBody(BaseModel):
    path: str


class CreateWorkspaceBody(BaseModel):
    path: str


class SelectDirectoryBody(BaseModel):
    initialPath: str | None = None


def _validate_workspace(path: str) -> Path:
    ws = Path(path).expanduser().resolve()
    if not ws.exists():
        raise HTTPException(
            404,
            {
                "code": "workspace_not_found",
                "message": f"Workspace does not exist: {path}",
            },
        )
    if not ws.is_dir():
        raise HTTPException(
            400,
            {
                "code": "workspace_not_directory",
                "message": f"Workspace is not a directory: {path}",
            },
        )
    if not (ws / "skills").is_dir():
        raise HTTPException(
            400,
            {
                "code": "workspace_invalid",
                "message": f"Workspace must contain a skills/ directory: {path}",
            },
        )
    return ws


@router.get("/current")
def current_workspace():
    """Return the currently configured workspace pointer."""
    cfg = load_config()
    workspace = cfg.workspace_path
    resolved = str(Path(workspace).expanduser().resolve()) if workspace else None
    return {
        "workspace_path": workspace,
        "resolved_path": resolved,
        "configured": workspace is not None,
    }


@router.post("/create")
def create_workspace(body: CreateWorkspaceBody):
    """Create and select a new workspace."""
    try:
        result = importer.create_workspace(body.path)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    try:
        init_self_skill(result["workspace_path"])
    except Exception:
        pass
    return {
        "success": True,
        **result,
    }


@router.post("/switch")
def switch_workspace(body: SwitchWorkspaceBody):
    """Switch the active workspace pointer."""
    ws = _validate_workspace(body.path)
    cfg = load_config()
    cfg.workspace_path = str(ws)
    save_config(cfg)
    try:
        init_self_skill(str(ws))
    except Exception:
        pass
    return {
        "success": True,
        "workspace_path": str(ws),
    }


@router.post("/select-directory")
def select_workspace_directory(body: SelectDirectoryBody):
    """Open the local system directory picker for workspace selection."""
    try:
        selected = select_directory(body.initialPath)
    except DirectoryPickerUnavailableError as exc:
        raise HTTPException(
            501,
            {
                "code": "directory_picker_unavailable",
                "message": str(exc),
            },
        ) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(500, str(exc)) from exc

    return {
        "success": True,
        "cancelled": selected is None,
        "path": selected,
    }
