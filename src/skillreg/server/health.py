"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from ..config import CONFIG_FILE, load_config

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health() -> dict:
    """Return service status + the configured workspace pointer."""
    cfg = load_config()
    workspace = cfg.workspace_path
    if workspace:
        return {"status": "ok", "workspace_path": workspace}
    return {
        "status": "ok",
        "workspace_path": None,
        "message": (
            "workspace not configured; set workspace_path in "
            f"{CONFIG_FILE} or via `skillreg config`."
        ),
    }
