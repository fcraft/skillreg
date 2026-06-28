"""Git API routes — ported from agent-hub ``routes/git.js``.

Returns git log for main repo and submodules.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from ..config import load_config
from ..services.skill_registry import read_submodule_configs

router = APIRouter(prefix="/api/git", tags=["git"])

_SEP = "<SEP>"
_FMT = f"%H{_SEP}%s{_SEP}%an{_SEP}%aI"


def _parse_logs(raw: str) -> list[dict]:
    entries = []
    for line in raw.strip().split("\n"):
        if not line:
            continue
        parts = line.split(_SEP)
        if len(parts) >= 4:
            entries.append({
                "hash": parts[0],
                "message": parts[1] or "",
                "author": parts[2] or "",
                "date": parts[3] or "",
            })
    return entries


def _run_git_log(ws: Path, cwd: Path | None = None, n: int = 15) -> list[dict]:
    try:
        result = subprocess.run(
            ["git", "log", f"--format={_FMT}", "-n", str(n)],
            capture_output=True, text=True, cwd=str(cwd or ws), timeout=10,
        )
        return _parse_logs(result.stdout)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []


@router.get("/logs")
def git_logs(scope: str = Query("all"), path: str = Query(None)):
    """Get git commit history.

    scope: all | main | submodule
    """
    cfg = load_config()
    if not cfg.workspace_path:
        raise HTTPException(400, "Workspace not configured")
    ws = Path(cfg.workspace_path).expanduser().resolve()

    logs = {"main": [], "submodules": {}}

    if scope in ("main", "all"):
        logs["main"] = _run_git_log(ws)

    if scope == "submodule" and path:
        sm_ws = ws / path
        if sm_ws.is_dir():
            logs["submodules"][path] = _run_git_log(ws, cwd=sm_ws, n=10)
    elif scope == "all":
        configs = read_submodule_configs(ws)
        for sm in configs:
            sm_ws = ws / sm["path"]
            if sm_ws.is_dir():
                sub_log = _run_git_log(ws, cwd=sm_ws, n=10)
                if sub_log:
                    logs["submodules"][sm["path"]] = sub_log

    return logs
