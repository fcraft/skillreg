"""Files API routes — ported from agent-hub ``routes/files.js``."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..services import file_browser

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/tree")
def file_tree(root: str = Query(".")):
    """Get file tree (cached 30s, depth ≤ 4, nodes ≤ 300)."""
    try:
        tree = file_browser.build_tree(root)
        if tree is None:
            raise HTTPException(403, "Path is outside workspace")
        return tree
    except ValueError as e:
        raise HTTPException(403, str(e))


@router.get("/content")
def file_content(root: str = Query("."), path: str = Query(...)):
    """Read file content (≤ 100KB, binary detection, language recognition)."""
    try:
        return file_browser.read_file_content(root, path)
    except file_browser.FileTooLargeError as e:
        raise HTTPException(413, detail={"error": str(e), "size": e.size})
    except ValueError as e:
        raise HTTPException(400, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))
