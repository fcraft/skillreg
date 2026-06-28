"""Import API routes — ported from agent-hub ``routes/import.js``."""

from __future__ import annotations


from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from ..services import importer

router = APIRouter(prefix="/api/import", tags=["import"])


# ── request models ────────────────────────────────────────────────────

class ValidateBody(BaseModel):
    sourceType: str = ""
    sourcePath: str


class ExecuteBody(BaseModel):
    sourceType: str = ""
    sourcePath: str
    tempPath: str | None = None
    renameTo: str | None = None
    force: bool = False


class PreviewUpdateBody(BaseModel):
    sourcePath: str
    skillName: str


class ExecuteUpdateBody(BaseModel):
    sourcePath: str
    skillName: str
    tempPath: str | None = None


class GitCloneBody(BaseModel):
    url: str
    branch: str | None = None


class GitImportBody(BaseModel):
    mode: str  # "skill" or "submodule"
    url: str | None = None
    branch: str | None = None
    tempPath: str | None = None
    selectedSkills: list[str] | None = None
    targetDir: str | None = None
    targetPath: str | None = None


class CleanupBody(BaseModel):
    tempPath: str


class CreateWorkspaceBody(BaseModel):
    location: str


# ── routes ────────────────────────────────────────────────────────────


@router.post("/workspace/create")
def create_workspace(body: CreateWorkspaceBody):
    """Create a new workspace at the given location."""
    try:
        result = importer.create_workspace(body.location)
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/upload")
async def upload_zip(file: UploadFile):
    """Upload and extract a zip file."""
    if not file:
        raise HTTPException(400, "No file uploaded")

    content = await file.read()
    if len(content) < 4:
        raise HTTPException(400, "Invalid file: too small to be a zip")

    # Check PK signature
    if content[0] != 0x50 or content[1] != 0x4B:
        raise HTTPException(400, "File is not a valid ZIP archive")

    try:
        result = importer.extract_zip(content)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(400, str(e))


@router.post("/validate")
def validate_import(body: ValidateBody):
    """Validate an import source."""
    try:
        result = importer.validate_import_source(body.sourcePath)
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/execute")
def execute_import(body: ExecuteBody):
    """Execute a skill import."""
    try:
        result = importer.import_skill(
            source_path=body.sourcePath,
            temp_path=body.tempPath,
            rename_to=body.renameTo,
            force=body.force,
        )
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/preview-update")
def preview_update(body: PreviewUpdateBody):
    """Preview changes for a skill update."""
    try:
        result = importer.preview_update(body.sourcePath, body.skillName)
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/execute-update")
def execute_update(body: ExecuteUpdateBody):
    """Execute a skill update."""
    try:
        result = importer.execute_update(
            body.sourcePath, body.skillName, body.tempPath,
        )
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/git-clone")
def git_clone(body: GitCloneBody):
    """Clone a git repo and discover skills."""
    try:
        result = importer.git_clone_to_temp(body.url, body.branch)
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/git-import")
def git_import(body: GitImportBody):
    """Execute git import (skill or submodule mode)."""
    try:
        if body.mode == "submodule":
            if not body.url or not body.targetPath:
                raise HTTPException(400, "url and targetPath are required for submodule mode")
            result = importer.git_import_as_submodule(body.url, body.targetPath, body.branch)
        else:
            if not body.tempPath or not body.selectedSkills:
                raise HTTPException(400, "tempPath and selectedSkills are required for skill mode")
            result = importer.git_import_skills(
                body.tempPath, body.selectedSkills, body.targetDir or "third",
            )
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/cleanup")
def cleanup(body: CleanupBody):
    """Clean up temp directory."""
    try:
        importer.cleanup_temp(body.tempPath)
        return {"success": True, "data": {"cleaned": True}}
    except ValueError as e:
        raise HTTPException(400, str(e))
