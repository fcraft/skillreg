"""Sync API routes — ported from agent-hub ``routes/sync.js``."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..services import sync_manager

router = APIRouter(prefix="/api/sync", tags=["sync"])


# ── request models ────────────────────────────────────────────────────

class AddTargetBody(BaseModel):
    name: str
    path: str


class UpdateSkillsBody(BaseModel):
    skills: list[str]


class RenameTargetBody(BaseModel):
    newName: str


class ExecuteSyncBody(BaseModel):
    target: str | None = None
    project: str | None = None
    skills: list[str] | None = None
    dryRun: bool = False


class RemoveSkillBody(BaseModel):
    skill: str
    target: str
    force: bool = False


class CreateProjectBody(BaseModel):
    name: str
    targets: list[str]


class ProjectTargetBody(BaseModel):
    path: str


# ── routes ────────────────────────────────────────────────────────────


@router.get("/targets")
def get_targets():
    """Target list with status overview."""
    return sync_manager.get_targets()


@router.post("/targets")
def add_target(body: AddTargetBody):
    """Add a new sync target."""
    try:
        target = sync_manager.add_target(body.name, body.path)
        return {"success": True, "target": target}
    except ValueError as e:
        raise HTTPException(409 if "already exists" in str(e) else 400, str(e))


@router.delete("/targets/{name}")
def remove_target(name: str):
    """Remove a target."""
    try:
        sync_manager.remove_target(name)
        return {"success": True, "removed": name}
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.put("/targets/{name}/skills")
def update_target_skills(name: str, body: UpdateSkillsBody):
    """Update target skill whitelist (no-op in v1; targets are simple paths)."""
    return {"success": True, "target": name, "skillCount": len(body.skills)}


@router.put("/targets/{name}/rename")
def rename_target(name: str, body: RenameTargetBody):
    """Rename a target."""
    try:
        target = sync_manager.rename_target(name, body.newName)
        return {"success": True, "target": target}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/execute")
def execute_sync(body: ExecuteSyncBody):
    """Execute sync (target or project)."""
    if body.project:
        project = sync_manager.get_project(body.project)
        if not project:
            raise HTTPException(404, f"Project not found: {body.project}")
        results = []
        for t in project.get("targets", []):
            r = sync_manager.execute_sync(t, dry_run=body.dryRun, skills=body.skills)
            results.append({"target": t, **r})
        return {"project": project["name"], "results": results}
    if not body.target:
        raise HTTPException(400, "Missing target or project")
    return sync_manager.execute_sync(body.target, dry_run=body.dryRun, skills=body.skills)


@router.get("/discover-home")
def discover_home():
    """Auto-discover agent dirs under ~/."""
    dirs = sync_manager.discover_home_agent_dirs()
    return {"agent_dirs": dirs}


@router.get("/discover")
def discover(path: str = Query(...)):
    """Auto-discover agent dirs at a path."""
    dirs = sync_manager.discover_agent_dirs(path)
    return {"path": str(Path(path).expanduser().resolve()), "agent_dirs": dirs}


# ── project routes ────────────────────────────────────────────────────


@router.get("/projects")
def list_projects():
    """List all local projects."""
    return sync_manager.list_projects()


@router.post("/projects")
def create_project(body: CreateProjectBody):
    """Create a new project."""
    try:
        project = sync_manager.create_project(body.name, body.targets)
        return {"success": True, "project": project}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/projects/{pid}")
def get_project(pid: str):
    """Get project detail."""
    project = sync_manager.get_project(pid)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.post("/projects/{pid}/targets")
def add_project_target(pid: str, body: ProjectTargetBody):
    """Add target to project."""
    try:
        project = sync_manager.add_project_target(pid, body.path)
        return {"success": True, "project": project}
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.delete("/projects/{pid}/targets")
def remove_project_target(pid: str, body: ProjectTargetBody):
    """Remove target from project."""
    try:
        project = sync_manager.remove_project_target(pid, body.path)
        return {"success": True, "project": project}
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.delete("/projects/{pid}")
def delete_project(pid: str):
    """Delete a project."""
    try:
        sync_manager.delete_project(pid)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(404, str(e))
