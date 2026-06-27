"""FastAPI backend for skillreg.

Exposes API routes under ``/api`` and (when present) serves the built dashboard
static files via ``StaticFiles``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .. import __version__


def dashboard_dir() -> Optional[Path]:
    """Locate the dashboard static directory."""
    env = os.environ.get("SKILLREG_DASHBOARD_DIR")
    if env:
        p = Path(env)
        if p.is_dir():
            return p
    dev = Path(__file__).resolve().parents[3] / "dashboard"
    if dev.is_dir():
        return dev
    return None


def create_app() -> FastAPI:
    """Build the FastAPI application with all routes mounted."""
    app = FastAPI(title="skillreg", version=__version__)

    # Inject self-skill on startup if workspace is configured
    from ..config import load_config
    from ..services.self_skill import init_self_skill

    cfg = load_config()
    if cfg.workspace_path:
        try:
            init_self_skill(cfg.workspace_path)
        except Exception:
            pass  # Non-fatal: dashboard still works without self-skill

    # Register route modules
    from .health import router as health_router

    app.include_router(health_router)

    # Skills / registry / sync routes (built progressively)
    try:
        from .skills import router as skills_router
        app.include_router(skills_router)
    except ImportError:
        pass

    try:
        from .sync import router as sync_router
        app.include_router(sync_router)
    except ImportError:
        pass

    try:
        from .registry import router as registry_router
        app.include_router(registry_router)
    except ImportError:
        pass

    try:
        from .files import router as files_router
        app.include_router(files_router)
    except ImportError:
        pass

    try:
        from .git import router as git_router
        app.include_router(git_router)
    except ImportError:
        pass

    try:
        from .submodules import router as submodules_router
        app.include_router(submodules_router)
    except ImportError:
        pass

    try:
        from .hooks import router as hooks_router
        app.include_router(hooks_router)
    except ImportError:
        pass

    try:
        from .import_ import router as import_router
        app.include_router(import_router)
    except ImportError:
        pass

    # Dashboard static mount (catch-all, after /api routes)
    _d = dashboard_dir()
    if _d is not None:
        app.mount("/", StaticFiles(directory=str(_d), html=True), name="dashboard")

    return app


# Module-level app for uvicorn (skillreg.server:app)
app = create_app()
