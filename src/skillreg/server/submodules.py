"""Submodule API routes — ported from agent-hub ``routes/submodules.js``.

Provides submodule listing, sync preview/execute, diff, refresh, and fix-detached.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from ..config import load_config
from ..services.skill_registry import (
    get_submodule_status,
    read_submodule_configs,
    _get_submodule_branch,
    _is_head_detached,
    _get_submodule_index_status,
)

router = APIRouter(prefix="/api/submodules", tags=["submodules"])


class SubmodulePathBody(BaseModel):
    path: str


class SyncBody(BaseModel):
    path: str
    commitMessage: str | None = None


def _ws() -> Path:
    cfg = load_config()
    if not cfg.workspace_path:
        raise HTTPException(400, "Workspace not configured")
    return Path(cfg.workspace_path).expanduser().resolve()


def _run(cmd: str, cwd: str, timeout: int = 30) -> str:
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        cwd=cwd, timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"Command failed: {cmd}")
    return result.stdout.strip()


@router.get("")
def list_submodules():
    """List all submodules with status."""
    ws = _ws()
    configs = read_submodule_configs(ws)
    result = []
    for sub in configs:
        status = get_submodule_status(ws, sub["path"], sub["branch"])
        result.append({
            "path": sub["path"],
            "branch": sub["branch"],
            "description": sub["description"],
            "status": status,
        })
    return result


@router.post("/sync-preview")
def preview_sync(body: SubmodulePathBody):
    """Preview sync actions without executing."""
    ws = _ws()
    path = body.path
    configs = read_submodule_configs(ws)
    sm = next((s for s in configs if s["path"] == path), None)
    if not sm:
        raise HTTPException(400, f"Unknown submodule: {path}")
    cwd = str(ws / path)
    if not (ws / path).is_dir():
        raise HTTPException(400, f"Directory not found: {path}")

    branch = sm["branch"]
    actions = []
    warnings = []

    # Fetch
    _run("git fetch origin", cwd)

    # Check detached
    detached = _is_head_detached(ws, path)
    if detached:
        actions.append(f"修复 detached HEAD → checkout {branch}")

    # Check dirty
    porcelain = _run("git status --porcelain", cwd)
    parsed = _parse_porcelain(porcelain)
    tracked = [p for p in parsed if not p["untracked"]]
    has_untracked = any(p["untracked"] for p in parsed)
    dirty = len(tracked) > 0
    dirty_files = [p["path"] for p in tracked]
    if dirty:
        actions.append(f"提交 {len(tracked)} 个修改的文件 (git add -u)")
    if has_untracked and not dirty:
        actions.append("有未跟踪文件（将跳过）")

    # Check ahead/behind
    ahead = 0
    behind = 0
    try:
        counts = _run(f"git rev-list --left-right --count HEAD...origin/{branch}", cwd)
        parts = counts.split("\t")
        ahead = int(parts[0]) if parts else 0
        behind = int(parts[1]) if len(parts) > 1 else 0
    except RuntimeError:
        pass

    needs_confirmation = False
    if behind > 0 and ahead > 0:
        actions.append(f"rebase 合并 {ahead} 个本地提交 onto {behind} 个远程提交")
        warnings.append(f"分叉状态：本地 {ahead} 提交，远程 {behind} 提交，需要 rebase")
        needs_confirmation = True
    elif behind > 0:
        actions.append(f"拉取 {behind} 个远程提交")
    elif ahead > 0:
        actions.append(f"推送 {ahead} 个本地提交到远程")

    # Pointer offset
    idx = _get_submodule_index_status(ws, path)
    needs_pointer = False
    if idx["indexBehind"] > 0:
        actions.append(f"更新主仓库子模块指针（落后 {idx['indexBehind']} 个提交）")
        needs_pointer = True
    elif idx["indexAhead"] > 0:
        actions.append(f"主仓库指针领先子模块 HEAD {idx['indexAhead']} 个提交（异常，需检查）")
        warnings.append("主仓库记录的提交领先于子模块 HEAD，建议人工确认")
        needs_pointer = True
    elif idx["indexDirty"]:
        actions.append("提交主仓库中待提交的子模块指针变更")
        needs_pointer = True

    if ahead > 0 or behind > 0 or dirty or needs_pointer:
        actions.append("更新主仓库子模块指针")

    if not actions:
        actions.append("已是最新，无需同步")

    return {
        "path": path,
        "branch": branch,
        "ahead": ahead,
        "behind": behind,
        "dirty": dirty,
        "dirtyFiles": dirty_files,
        "detached": detached,
        "indexAhead": idx["indexAhead"],
        "indexBehind": idx["indexBehind"],
        "indexDirty": idx["indexDirty"],
        "actions": actions,
        "warnings": warnings,
        "needsConfirmation": needs_confirmation,
    }


@router.post("/diff")
def submodule_diff(body: SubmodulePathBody):
    """Read-only diff of dirty tracked files in a submodule."""
    ws = _ws()
    path = body.path
    configs = read_submodule_configs(ws)
    sm = next((s for s in configs if s["path"] == path), None)
    if not sm:
        raise HTTPException(400, f"Unknown submodule: {path}")
    cwd = str(ws / path)
    if not (ws / path).is_dir():
        raise HTTPException(400, f"Directory not found: {path}")

    porcelain = _run("git status --porcelain", cwd)
    files = [p for p in _parse_porcelain(porcelain) if not p["untracked"]]

    result_files = []
    for f in files:
        xy = f["raw"].strip()
        status = "modified"
        if "D" in xy:
            status = "deleted"
        elif "A" in xy:
            status = "added"
        elif "R" in xy:
            status = "renamed"
        try:
            diff = _run(f'git diff HEAD -- "{f["path"]}"', cwd)
        except RuntimeError:
            diff = ""
        result_files.append({"path": f["path"], "status": status, "diff": diff})

    return {"path": path, "branch": sm["branch"], "files": result_files}


@router.post("/sync")
def sync_submodule(body: SyncBody):
    """Run a best-effort submodule sync update flow."""
    ws = _ws()
    path = body.path
    cwd = str(ws / path)
    if not (ws / path).is_dir():
        raise HTTPException(400, f"Directory not found: {path}")
    branch = _get_submodule_branch(ws, path)
    steps = []
    try:
        _run("git fetch origin", cwd)
        steps.append("fetch")
    except RuntimeError as e:
        raise HTTPException(400, str(e))

    if _is_head_detached(ws, path):
        _run(f"git checkout {branch}", cwd)
        steps.append("checkout")

    return {
        "success": True,
        "path": path,
        "branch": branch,
        "steps": steps,
        "commitMessage": body.commitMessage,
    }


@router.post("/refresh")
def refresh_submodule(body: dict | None = Body(default=None)):
    """Refresh one submodule, or all submodules when path is omitted."""
    ws = _ws()
    configs = read_submodule_configs(ws)
    path = body.get("path") if isinstance(body, dict) else None

    if path:
        sm = next((s for s in configs if s["path"] == path), None)
        if not sm:
            raise HTTPException(400, f"Unknown submodule: {path}")
        cwd = str(ws / path)
        try:
            _run("git fetch origin", cwd)
        except RuntimeError:
            pass
        return {
            "path": path,
            "status": get_submodule_status(ws, path, sm["branch"]),
            "error": None,
        }

    results = []
    for sm in configs:
        sub_path = sm["path"]
        cwd = str(ws / sub_path)
        error = None
        try:
            _run("git fetch origin", cwd)
        except RuntimeError as exc:
            error = str(exc)
        results.append({
            "path": sub_path,
            "status": get_submodule_status(ws, sub_path, sm["branch"]),
            "error": error,
        })

    return {
        "results": results,
        "checkedAt": int(time.time() * 1000),
    }


@router.post("/fix-detached")
def fix_detached(body: SubmodulePathBody):
    """Fix detached HEAD for a submodule."""
    ws = _ws()
    path = body.path
    cwd = str(ws / path)
    if not (ws / path).is_dir():
        raise HTTPException(400, f"Directory not found: {path}")
    if not _is_head_detached(ws, path):
        return {"fixed": False, "message": "HEAD is not detached"}

    branch = _get_submodule_branch(ws, path)
    before = _run("git rev-parse --short HEAD", cwd)
    _run(f"git checkout {branch}", cwd)
    after = _run("git rev-parse --short HEAD", cwd)
    return {"fixed": True, "branch": branch, "before": before, "after": after}


def _parse_porcelain(porcelain: str) -> list[dict]:
    import re
    results = []
    for line in porcelain.split("\n"):
        if not line:
            continue
        if line.startswith("??"):
            m = re.match(r"^\?\?\s+(.+)$", line)
            if m:
                results.append({"raw": "??", "path": m.group(1), "untracked": True})
        else:
            m = re.match(r"^([MADRC?! ]?)([MADRC?!])\s+(.+)$", line)
            if m:
                results.append({"raw": (m.group(1) or " ") + m.group(2), "path": m.group(3), "untracked": False})
    return results
