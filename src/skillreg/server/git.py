"""Git API routes.

Returns git log for main repo and submodules.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..config import load_config
from ..services.skill_registry import read_submodule_configs

router = APIRouter(prefix="/api/git", tags=["git"])

_SEP = "<SEP>"
_FMT = f"%H{_SEP}%s{_SEP}%an{_SEP}%aI"


class GitIdentityBody(BaseModel):
    repository: str = "."
    name: str
    email: str


def _workspace() -> Path:
    cfg = load_config()
    if not cfg.workspace_path:
        raise HTTPException(400, "Workspace not configured")
    return Path(cfg.workspace_path).expanduser().resolve()


def _repository(ws: Path, relative: str) -> tuple[Path, str]:
    target = (ws / relative).resolve()
    if target != ws and ws not in target.parents:
        raise HTTPException(400, "Repository must be inside the current workspace")
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=target,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if result.returncode or Path(result.stdout.strip()).resolve() != target:
        raise HTTPException(400, "Path is not a Git repository root")
    normalized = target.relative_to(ws).as_posix() or "."
    return target, normalized


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
            capture_output=True,
            text=True,
            cwd=str(cwd or ws),
            check=False,
            timeout=10,
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


@router.post("/identity")
def set_git_identity(body: GitIdentityBody):
    name = body.name.strip()
    email = body.email.strip()
    if not name or any(char in name for char in "\r\n"):
        raise HTTPException(422, "Git user.name cannot be empty")
    if "@" not in email or any(char in email for char in "\r\n"):
        raise HTTPException(422, "Enter a valid Git user.email")
    repo, repository = _repository(_workspace(), body.repository)
    try:
        subprocess.run(
            ["git", "config", "--local", "user.name", name],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        subprocess.run(
            ["git", "config", "--local", "user.email", email],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(400, f"Unable to save Git identity: {exc}") from exc
    return {
        "success": True,
        "repository": repository,
        "name": name,
        "email": email,
    }
