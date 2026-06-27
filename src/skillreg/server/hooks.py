"""Hooks API routes — ported from agent-hub ``routes/hooks.js``.

Integrates the hooks management logic from ``infra/hooks.py``.
Uses subprocess for scan/status/install/uninstall/validate operations.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/hooks", tags=["hooks"])


class HookActionBody(BaseModel):
    hookId: str
    local: bool = False
    dryRun: bool = False


def _find_hooks_script() -> Path:
    """Find the hooks.py script."""
    candidates = [
        Path(__file__).resolve().parents[4] / "infra" / "hooks.py",  # agent-hub-kex
        Path.home() / "Code/project_kex/agent-hub/infra/hooks.py",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError("hooks.py not found")


def _run_hooks(*args: str, timeout: int = 30) -> dict:
    script = _find_hooks_script()
    result = subprocess.run(
        ["python3", str(script), "--json", *args],
        capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "hooks.py failed")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"raw_output": result.stdout}


@router.get("/scan")
def scan_hooks():
    """Scan available hook scripts."""
    try:
        return _run_hooks("scan")
    except (RuntimeError, FileNotFoundError) as e:
        raise HTTPException(500, str(e))


@router.get("/status")
def hook_status(local: int = 0):
    """Full status — available + installed + third-party."""
    try:
        args = ["status"]
        if local:
            args.append("--local")
        return _run_hooks(*args)
    except (RuntimeError, FileNotFoundError) as e:
        raise HTTPException(500, str(e))


@router.get("")
def fetch_hooks(local: int = 0):
    """Alias for /api/hooks/status."""
    return hook_status(local)


@router.post("/install")
def install_hook(body: HookActionBody):
    """Install a hook.

    Fixes v1 contract gap: uses hookId (frontend convention).
    """
    try:
        args = ["install", body.hookId]
        if body.local:
            args.append("--local")
        if body.dryRun:
            args.append("--dry-run")
        return _run_hooks(*args)
    except (RuntimeError, FileNotFoundError) as e:
        raise HTTPException(500, str(e))


@router.post("/uninstall")
def uninstall_hook(body: HookActionBody):
    """Uninstall a hook."""
    try:
        args = ["uninstall", body.hookId]
        if body.local:
            args.append("--local")
        if body.dryRun:
            args.append("--dry-run")
        return _run_hooks(*args)
    except (RuntimeError, FileNotFoundError) as e:
        raise HTTPException(500, str(e))


@router.post("/validate")
def validate_hooks():
    """Validate installed hook scripts exist.

    Fixes v1 contract gap: uses POST (not GET) with --json output.
    """
    try:
        return _run_hooks("validate")
    except (RuntimeError, FileNotFoundError) as e:
        raise HTTPException(500, str(e))
