"""FastAPI backend for skillreg.

Exposes API routes under ``/api`` and (when present) serves the built dashboard
static files via ``StaticFiles``. The dashboard is a placeholder in M1; a later
issue migrates the real Vue build output here.

``/api/health`` reports the current workspace pointer from
``~/.skillreg/config.json`` (null + message when unconfigured).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import CONFIG_FILE, load_config

app = FastAPI(title="skillreg", version=__version__)


# --- dashboard static dir discovery ----------------------------------------


def dashboard_dir() -> Optional[Path]:
    """Locate the dashboard static directory.

    Resolution order:
    1. ``$SKILLREG_DASHBOARD_DIR`` env var (explicit override, used by tests).
    2. ``<repo-root>/dashboard`` — the dev/editable-install location.

    Returns ``None`` when no dashboard directory is found (M1 may still run
    without a built frontend; only ``/api/*`` is served then).
    """
    env = os.environ.get("SKILLREG_DASHBOARD_DIR")
    if env:
        p = Path(env)
        if p.is_dir():
            return p
    # src/skillreg/server.py -> parents[0]=skillreg, [1]=src, [2]=repo root
    dev = Path(__file__).resolve().parents[2] / "dashboard"
    if dev.is_dir():
        return dev
    return None


# --- API routes ------------------------------------------------------------


@app.get("/api/health")
def health() -> dict:
    """Return service status + the configured workspace pointer.

    Response shape (PRD §2.3 / issue #02 acceptance):
    - ``status``: always ``"ok"`` when reachable.
    - ``workspace_path``: configured path string, or ``null``.
    - ``message``: present only when the workspace is not configured.
    """
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


# --- dashboard static mount (catch-all, registered after /api routes) -------

_d = dashboard_dir()
if _d is not None:
    app.mount("/", StaticFiles(directory=str(_d), html=True), name="dashboard")
