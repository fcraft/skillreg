"""Registry API routes — ported from agent-hub ``routes/registry.js``."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import load_config
from ..services import importer

router = APIRouter(prefix="/api/registry", tags=["registry"])


class RegisterBody(BaseModel):
    sourcePath: str
    force: bool = False


class ConvertBody(BaseModel):
    name: str


@router.post("/register")
def register_skill(body: RegisterBody):
    """Register an external skill into the workspace.
    """
    cfg = load_config()
    if not cfg.workspace_path:
        raise HTTPException(400, "Workspace not configured")
    try:
        result = importer.import_skill(body.sourcePath, force=body.force)
        return {"success": True, "data": result}
    except ValueError as exc:
        detail = str(exc)
        status = 409 if "already exists" in detail else 400
        raise HTTPException(status, detail) from exc


@router.post("/convert")
def convert_skill(body: ConvertBody):
    """Convert a file skill to a CLI repo.
    """
    cfg = load_config()
    if not cfg.workspace_path:
        raise HTTPException(400, "Workspace not configured")
    try:
        result = importer.convert_skill(body.name)
        return {"success": True, "data": result}
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except FileExistsError as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/list")
def list_registered():
    """List all registered skills."""
    try:
        from ..services.skill_registry import get_all
        from pathlib import Path

        cfg = load_config()
        if not cfg.workspace_path:
            raise HTTPException(400, "Workspace not configured")
        ws = Path(cfg.workspace_path).expanduser().resolve()
        data = get_all(ws)
        return {"success": True, "data": {"skills": data["skills"]}}
    except Exception as e:
        return {"success": False, "error": str(e)}
