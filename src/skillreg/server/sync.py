"""Sync API routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..services import sync_manager
from ..services.sync_files import SyncError

router = APIRouter(prefix="/api/sync", tags=["sync"])


def raise_sync_http_error(exc: Exception) -> None:
    """Translate sync domain and filesystem errors into structured HTTP errors."""
    if isinstance(exc, SyncError):
        status = (
            404
            if exc.code == "not-found"
            else 403
            if exc.code == "permission-denied"
            else 409
            if exc.code
            in {
                "conflict",
                "ambiguous-target",
                "target-busy",
                "target-changed",
                "source-changed",
                "preview-expired",
            }
            else 400
        )
        raise HTTPException(
            status,
            {"code": exc.code, "message": str(exc), "retryable": exc.retryable},
        ) from exc
    if isinstance(exc, PermissionError):
        raise HTTPException(
            403,
            {"code": "permission-denied", "message": str(exc), "retryable": False},
        ) from exc
    if isinstance(exc, (ValueError, OSError)):
        raise HTTPException(
            400,
            {"code": "sync-failed", "message": str(exc), "retryable": False},
        ) from exc
    raise exc


# ── request models ────────────────────────────────────────────────────

class AddTargetBody(BaseModel):
    name: str
    path: str
    agentKind: str | None = None


class UpdateBuiltinAgentBody(BaseModel):
    enabled: bool


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


@router.get("/config")
def get_config():
    """Get synthesized sync config."""
    return sync_manager.get_sync_config()


@router.get("/status")
def get_status(
    target: str | None = Query(None),
    include_projects: bool = Query(False, alias="include_projects"),
    skill: str | None = Query(None),
):
    """Per-target per-skill sync status."""
    return sync_manager.get_sync_status(
        target=target,
        include_projects=include_projects,
        skill=skill,
    )


@router.post("/targets")
def add_target(body: AddTargetBody):
    """Add a new sync target."""
    try:
        target = sync_manager.add_target(body.name, body.path, agent_kind=body.agentKind)
        return {"success": True, "target": target}
    except ValueError as e:
        is_conflict = getattr(e, "code", None) == "conflict" or "already exists" in str(e)
        raise HTTPException(409 if is_conflict else 400, str(e))


@router.delete("/targets/{name:path}")
def remove_target(name: str):
    """Remove a target."""
    try:
        sync_manager.remove_target(name)
        return {"success": True, "removed": name}
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.put("/targets/{name:path}/skills")
def update_target_skills(name: str, body: UpdateSkillsBody):
    """Update target skill whitelist."""
    try:
        result = sync_manager.update_target_skills(name, body.skills)
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.put("/targets/{name:path}/rename")
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
            try:
                r = sync_manager.execute_sync(t, dry_run=body.dryRun, skills=body.skills)
                results.append({"target": t, **r})
            except (SyncError, ValueError, OSError) as exc:
                results.append({
                    "target": t,
                    "success": False,
                    "stdout": "",
                    "stderr": str(exc),
                    "code": getattr(exc, "code", "permission-denied" if isinstance(exc, PermissionError) else "sync-failed"),
                })
        return {"project": project["name"], "results": results}
    if not body.target:
        raise HTTPException(400, {"code": "invalid", "message": "Missing target or project", "retryable": False})
    try:
        return sync_manager.execute_sync(body.target, dry_run=body.dryRun, skills=body.skills)
    except (SyncError, ValueError, OSError) as exc:
        raise_sync_http_error(exc)


@router.get("/skill-presence")
def skill_presence(skill: str = Query(...)):
    """Query which targets contain a skill."""
    try:
        return sync_manager.get_skill_presence(skill)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/target-skills")
def target_skills(target: str = Query(...)):
    """List skills inside a target."""
    try:
        return sync_manager.list_target_skills(target)
    except (SyncError, ValueError, OSError) as exc:
        raise_sync_http_error(exc)


@router.get("/diff")
def skill_diff(skill: str = Query(...), target: str = Query(...)):
    """Compare a workspace skill against the target copy."""
    try:
        files = sync_manager.get_skill_diff(skill, target)
        summary = {}
        for f in files:
            summary[f["status"]] = summary.get(f["status"], 0) + 1
        return {"files": files, "summary": summary}
    except (SyncError, ValueError, OSError) as exc:
        raise_sync_http_error(exc)


@router.post("/remove-skill")
def remove_skill(body: RemoveSkillBody):
    """Remove a skill from a target."""
    try:
        return sync_manager.remove_skill_from_target(body.skill, body.target, force=body.force)
    except (SyncError, ValueError, OSError) as exc:
        raise_sync_http_error(exc)


@router.get("/target-file")
def target_file(
    skill: str = Query(...),
    target: str = Query(...),
    path: str = Query(...),
):
    """Read a file from the target-side skill copy."""
    try:
        return sync_manager.get_target_file(skill, target, path)
    except (SyncError, ValueError, OSError) as exc:
        raise_sync_http_error(exc)


@router.get("/agents")
def list_builtin_agents(
    include_undetected: bool = Query(True),
    include_legacy: bool = Query(False),
):
    """List built-in coding agent directory conventions and local detection status."""
    return sync_manager.list_builtin_agents(
        include_undetected=include_undetected,
        include_legacy=include_legacy,
    )


@router.put("/agents/{agent_id}")
def update_builtin_agent(agent_id: str, body: UpdateBuiltinAgentBody):
    """Enable or hide an auto-detected built-in agent target."""
    try:
        result = sync_manager.set_builtin_agent_enabled(agent_id, body.enabled)
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/discover-home")
def discover_home(include_undetected: bool = Query(False)):
    """Auto-discover built-in agent dirs under ~/."""
    dirs = sync_manager.discover_home_agent_dirs(include_undetected=include_undetected)
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
