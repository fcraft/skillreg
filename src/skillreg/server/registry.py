"""Registry API routes — ported from agent-hub ``routes/registry.js``."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import load_config

router = APIRouter(prefix="/api/registry", tags=["registry"])


class RegisterBody(BaseModel):
    sourcePath: str
    force: bool = False


class ConvertBody(BaseModel):
    name: str


@router.post("/register")
def register_skill(body: RegisterBody):
    """Register an external skill into the workspace.

    Placeholder for now; full implementation in Issue #4.
    """
    cfg = load_config()
    if not cfg.workspace_path:
        raise HTTPException(400, "Workspace not configured")
    # TODO: Implement registerSkill in Issue #4
    return {
        "success": False,
        "error": "Skill registration not yet implemented (coming in Issue #4)",
    }


@router.post("/convert")
def convert_skill(body: ConvertBody):
    """Convert a file skill to a CLI repo.

    Placeholder for now.
    """
    return {
        "success": False,
        "error": "Skill conversion not yet implemented",
    }


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
