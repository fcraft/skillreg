"""Backward-compatible dashboard routes mapped to the new FastAPI API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..services import sync_manager
from .skills import skill_tree, skill_file, refresh_skills

router = APIRouter(tags=["compat"])


@router.get("/api/skill-tree")
def compat_skill_tree(skill: str = Query(...)):
    return skill_tree(skill)


@router.get("/api/skill-file")
def compat_skill_file(skill: str = Query(...), path: str = Query(...)):
    return skill_file(skill, path)


@router.get("/api/skill-sync-targets")
def compat_sync_targets():
    return sync_manager.get_targets()


@router.post("/api/sync-skills")
def compat_sync_skills(target: str = Query(...), dry_run: bool = Query(False, alias="dryRun")):
    return sync_manager.execute_sync(target, dry_run=dry_run)


@router.get("/api/refresh-data")
def compat_refresh_data():
    return refresh_skills()


@router.get("/api/skill-target-file")
def compat_target_file(
    skill: str = Query(...),
    target: str = Query(...),
    path: str = Query(...),
):
    try:
        return sync_manager.get_target_file(skill, target, path)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/api/skill-diff")
def compat_skill_diff(skill: str = Query(...), target: str = Query(...)):
    try:
        return sync_manager.get_skill_diff(skill, target)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/api/skill-target-presence")
def compat_skill_presence(skill: str = Query(...)):
    try:
        return sync_manager.get_skill_presence(skill)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/api/target-skills")
def compat_target_skills(target: str = Query(...)):
    return sync_manager.list_target_skills(target)


@router.post("/api/remove-skill-from-target")
def compat_remove_skill_from_target(
    skill: str = Query(...),
    target: str = Query(...),
    force: bool = Query(False),
):
    return sync_manager.remove_skill_from_target(skill, target, force=force)
