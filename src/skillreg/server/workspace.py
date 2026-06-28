"""Workspace pointer management routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import load_config, save_config
from ..services.self_skill import init_self_skill

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


class SwitchWorkspaceBody(BaseModel):
    path: str


def _validate_workspace(path: str) -> Path:
    ws = Path(path).expanduser().resolve()
    if not ws.exists():
        raise HTTPException(400, f"Workspace does not exist: {path}")
    if not ws.is_dir():
        raise HTTPException(400, f"Workspace is not a directory: {path}")
    if not (ws / "skills").is_dir():
        raise HTTPException(400, f"Workspace must contain a skills/ directory: {path}")
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
