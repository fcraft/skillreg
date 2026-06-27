"""Skills API routes — ported from agent-hub ``routes/skills.js``."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from ..config import load_config
from ..services.skill_registry import get_all, get_skill

router = APIRouter(prefix="/api/skills", tags=["skills"])


def _workspace() -> Path:
    """Resolve the configured workspace path, or raise 400."""
    cfg = load_config()
    if not cfg.workspace_path:
        raise HTTPException(400, "Workspace not configured. Set workspace_path in config.")
    ws = Path(cfg.workspace_path).expanduser().resolve()
    if not ws.is_dir():
        raise HTTPException(400, f"Workspace directory not found: {ws}")
    return ws


@router.get("")
def list_skills(full: str = Query("0", alias="full")):
    """List skills — lightweight without ?full=1, full with ?full=1."""
    ws = _workspace()
    data = get_all(ws)
    if full == "1":
        return data
    return {"skills": data["skills"], "generatedAt": data["generatedAt"]}


@router.get("/refresh")
def refresh_skills():
    """Force refresh the skill registry."""
    ws = _workspace()
    # clear cache is not directly supported on get_all since it's not cached here;
    # but we can just re-call it
    return get_all(ws)


@router.get("/{skill_id}")
def skill_detail(skill_id: str):
    """Single skill detail."""
    ws = _workspace()
    skill = get_skill(ws, skill_id)
    if not skill:
        raise HTTPException(404, "Unknown skill")
    return skill


@router.get("/{skill_id}/relationships")
def skill_relationships(skill_id: str):
    """Relationships for a specific skill."""
    ws = _workspace()
    skill = get_skill(ws, skill_id)
    if not skill:
        raise HTTPException(404, "Unknown skill")
    data = get_all(ws)
    related = [
        r for r in data["relationships"]
        if r["from"] == skill_id or r["to"] == skill_id
        or r["from"] == skill.get("name") or r["to"] == skill.get("name")
    ]
    return {"skill": skill_id, "relationships": related}


@router.get("/{skill_id}/stats")
def skill_stats(skill_id: str):
    """Statistics for a specific skill."""
    ws = _workspace()
    skill = get_skill(ws, skill_id)
    if not skill:
        raise HTTPException(404, "Unknown skill")
    return {
        "name": skill["name"],
        "fileCount": skill["fileCount"],
        "type": skill["type"],
        "path": skill["path"],
    }
