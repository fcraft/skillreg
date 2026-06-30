"""Skills API routes — ported from agent-hub ``routes/skills.js``."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..config import load_config
from .git import git_logs
from ..services.skill_registry import get_all, get_skill
from ..services import file_browser, importer

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
        data["gitLogs"] = git_logs(scope="all", path=None)
        return data
    return {"skills": data["skills"], "generatedAt": data["generatedAt"]}


@router.get("/refresh")
def refresh_skills():
    """Force refresh the skill registry."""
    ws = _workspace()
    data = get_all(ws, force=True)
    data["gitLogs"] = git_logs(scope="all", path=None)
    return data


@router.get("/{skill_id}")
def skill_detail(skill_id: str):
    """Single skill detail."""
    ws = _workspace()
    skill = get_skill(ws, skill_id)
    if not skill:
        raise HTTPException(404, "Unknown skill")
    return skill


@router.delete("/{skill_id}")
def delete_skill(skill_id: str):
    """Delete a standalone skill from the workspace ``skills/`` directory.

    Skills that belong to a submodule/repo cannot be deleted here — remove the
    whole repo instead. Renaming skills is intentionally unsupported to avoid
    name collisions.
    """
    ws = _workspace()
    skill = get_skill(ws, skill_id)
    if not skill:
        raise HTTPException(404, "Unknown skill")
    if skill.get("isSubmodule"):
        raise HTTPException(
            400,
            "This skill belongs to a repo/submodule and cannot be deleted "
            "individually. Remove the whole repo instead.",
        )
    try:
        result = importer.delete_skill(skill["name"])
        return {"success": True, **result}
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


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


@router.get("/{skill_id}/tree")
def skill_tree(skill_id: str):
    """File tree rooted at the skill directory."""
    ws = _workspace()
    skill = get_skill(ws, skill_id)
    if not skill:
        raise HTTPException(404, "Unknown skill")
    tree = file_browser.build_tree(skill["path"])
    if tree is None:
        raise HTTPException(403, "Skill path is outside repository")
    return tree


@router.get("/{skill_id}/file")
def skill_file(skill_id: str, path: str = Query(...)):
    """Read a file inside a skill directory."""
    ws = _workspace()
    skill = get_skill(ws, skill_id)
    if not skill:
        raise HTTPException(404, "Unknown skill")
    try:
        return file_browser.read_file_content(skill["path"], path)
    except file_browser.FileTooLargeError as e:
        raise HTTPException(413, detail={"error": str(e), "size": e.size})
    except ValueError as e:
        if "Path is not a file" in str(e):
            return {"exists": False, "path": path}
        raise HTTPException(400, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))


@router.get("/{skill_id}/export")
def export_skill(skill_id: str):
    """Export a skill directory as a zip archive."""
    ws = _workspace()
    skill = get_skill(ws, skill_id)
    if not skill:
        raise HTTPException(404, "Unknown skill")

    skill_dir = (ws / skill["path"]).resolve()
    if not skill_dir.is_dir():
        raise HTTPException(404, "Unknown skill")
    try:
        skill_dir.relative_to(ws)
    except ValueError:
        raise HTTPException(403, "Skill path is outside repository")

    buffer = io.BytesIO()
    ignored_names = {".DS_Store", "Thumbs.db"}
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(skill_dir.rglob("*")):
            if not file_path.is_file():
                continue
            if any(part in {".git", "__MACOSX"} for part in file_path.parts):
                continue
            if file_path.name in ignored_names or file_path.name.startswith("._") or file_path.name.startswith(".icloud"):
                continue
            arcname = str(file_path.relative_to(skill_dir)).replace("\\", "/")
            zf.write(file_path, arcname)

    buffer.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="{skill["name"]}.zip"'}
    return StreamingResponse(buffer, media_type="application/zip", headers=headers)
