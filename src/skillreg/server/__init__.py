"""FastAPI backend for skillreg.

Exposes API routes under ``/api`` and (when present) serves the built dashboard
static files via ``StaticFiles``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .. import __version__


def dashboard_dir() -> Optional[Path]:
    """Locate the dashboard static directory."""
    env = os.environ.get("SKILLREG_DASHBOARD_DIR")
    if env:
        p = Path(env)
        if p.is_dir():
            return p
    # 1. 包内打包的构建产物（pip install 场景）
    packaged = Path(__file__).resolve().parent.parent / "dashboard_dist"
    if packaged.is_dir():
        return packaged
    # 2. 源码仓库中的构建产物（开发 / uv run 场景）
    dashboard_root = Path(__file__).resolve().parents[3] / "dashboard"
    dist = dashboard_root / "dist"
    if dist.is_dir():
        return dist
    if dashboard_root.is_dir():
        return dashboard_root
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

    try:
        from .compat import router as compat_router
        app.include_router(compat_router)
    except ImportError:
        pass

    try:
        from .workspace import router as workspace_router
        app.include_router(workspace_router)
    except ImportError:
        pass

    # Dashboard static serving (SPA fallback, after /api routes)
    _d = dashboard_dir()
    if _d is not None:
        index_file = _d / "index.html"
        if index_file.is_file():
            @app.get("/assets/{asset_path:path}", include_in_schema=False)
            def dashboard_assets(asset_path: str):
                file_path = (_d / "assets" / asset_path).resolve()
                assets_root = (_d / "assets").resolve()
                try:
                    file_path.relative_to(assets_root)
                except ValueError as exc:
                    raise HTTPException(404) from exc
                if not file_path.is_file():
                    raise HTTPException(404)
                return FileResponse(file_path)

            @app.get("/{full_path:path}", include_in_schema=False)
            def dashboard_spa_fallback(full_path: str):
                request_path = (_d / full_path).resolve()
                try:
                    request_path.relative_to(_d.resolve())
                except ValueError:
                    return FileResponse(index_file)
                if full_path and request_path.is_file():
                    return FileResponse(request_path)
                return FileResponse(index_file)

    return app


# Module-level app for uvicorn (skillreg.server:app)
app = create_app()
