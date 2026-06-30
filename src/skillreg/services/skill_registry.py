"""Skill registry service — ported from agent-hub ``skill-registry.js``.

Provides skill discovery, classification, and the ``getAll()`` aggregation that
powers the dashboard.  All paths are rooted at the user-configured workspace.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

import yaml

from .url_utils import normalize_git_url

# ── constants --------------------------------------------------------------

# Directories skipped during skill discovery
_IGNORED_SCAN_DIRS = frozenset({
    ".git", ".idea", ".codebuddy", "node_modules", "dashboard",
    ".venv", "venv", "__pycache__", "dist", "coverage",
})

# Directories skipped during file counting
_IGNORED_COUNT_DIRS = frozenset({
    ".git", "node_modules", ".venv", "venv",
    "__pycache__", "dist", "build", "coverage",
})

# Known hardcoded dependencies
_KNOWN_DEPENDENCIES: list[dict[str, str]] = [
    {"from": "ntcompose-build-page", "to": "ntdev-build", "type": "depends-on"},
]

# Agent conventions (same as sync-skills.py)
_AGENT_HUB_CONVENTIONS: list[tuple[str, str]] = [
    (".claude/skills", "claude"),
    (".tclaude/skills", "tclaude"),
    (".codebuddy/skills", "codebuddy"),
    (".codex/skills", "codex"),
    (".tcodex/skills", "tcodex"),
    (".agents/skills", "agents"),
    (".agent/skills", "agent"),
]

_CACHE_TTL_SECONDS = 30.0
_GET_ALL_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


# ── helpers ----------------------------------------------------------------

def _run(cmd: str, cwd: str | None = None, timeout: int = 30) -> str:
    """Run a shell command and return stripped stdout. Raises on failure."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        cwd=cwd, timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"Command failed: {cmd}")
    return result.stdout.strip()


def _parse_frontmatter(file_path: Path) -> dict[str, Any]:
    """Parse YAML frontmatter from a SKILL.md file."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        data = yaml.safe_load(parts[1])
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError:
        return {}


def _classify_skill_type(workspace: Path, dir_path: str) -> str:
    """Classify a skill as 'CLI' or 'Reference'.

    Searches upward from dir_path for pyproject.toml or src/*.py.
    """
    parts = [p for p in dir_path.split("/") if p]
    for i in range(len(parts), 0, -1):
        candidate = "/".join(parts[:i])
        full_dir = workspace / candidate
        if (full_dir / "pyproject.toml").exists():
            return "CLI"
        src_dir = full_dir / "src"
        if src_dir.is_dir():
            try:
                py_files = list(src_dir.rglob("*.py"))
                if len(py_files) > 0:
                    return "CLI"
            except OSError:
                pass
    return "Reference"


def _count_skill_files(root: Path, max_files: int = 200, max_depth: int = 6) -> int:
    """Count non-ignored files in a skill directory."""
    count = 0

    def visit(current: Path, depth: int) -> None:
        nonlocal count
        if count >= max_files or depth > max_depth:
            return
        try:
            entries = sorted(current.iterdir(), key=lambda e: e.name)
        except OSError:
            return
        for entry in entries:
            if count >= max_files:
                return
            if entry.is_dir():
                if entry.name in _IGNORED_COUNT_DIRS or entry.name.startswith("."):
                    continue
                visit(entry, depth + 1)
            elif entry.is_file():
                count += 1

    visit(root, 0)
    return count


# ── skill discovery ────────────────────────────────────────────────────────


def _discover_skill_paths(workspace: Path) -> list[str]:
    """Find all SKILL.md files under workspace, returning repo-relative paths."""
    results: list[str] = []

    def visit(current: Path) -> None:
        try:
            entries = sorted(current.iterdir(), key=lambda e: e.name)
        except OSError:
            return
        for entry in entries:
            if entry.is_dir():
                if entry.name in _IGNORED_SCAN_DIRS or entry.name.startswith("."):
                    continue
                visit(entry)
            elif entry.is_file() and entry.name == "SKILL.md":
                rel = str(entry.relative_to(workspace)).replace(os.sep, "/")
                results.append(rel)

    visit(workspace)
    return sorted(results)


# ── submodule config reading ───────────────────────────────────────────────


def _get_submodule_branch(workspace: Path, submodule_path: str) -> str:
    full = workspace / submodule_path
    if not full.is_dir():
        return "main"
    try:
        ref = _run("git rev-parse --abbrev-ref HEAD", cwd=str(full))
        if ref and ref != "HEAD":
            return ref
    except RuntimeError:
        pass
    return "main"


def _derive_submodule_description(workspace: Path, submodule_path: str) -> str:
    root = workspace / submodule_path
    if not root.is_dir():
        return ""
    # Check root-level SKILL.md
    root_skill = root / "SKILL.md"
    if root_skill.exists():
        parsed = _parse_frontmatter(root_skill)
        desc = parsed.get("description", "")
        if desc:
            return desc
    # Scan one level of subdirectories
    try:
        entries = sorted(root.iterdir())
    except OSError:
        return ""
    for entry in entries:
        if not entry.is_dir():
            continue
        skill_file = entry / "SKILL.md"
        if skill_file.exists():
            parsed = _parse_frontmatter(skill_file)
            desc = parsed.get("description", "")
            if desc:
                return desc
        # One level deeper (skill/<name>/SKILL.md pattern)
        try:
            sub_entries = sorted(entry.iterdir())
        except OSError:
            continue
        for sub in sub_entries:
            if not sub.is_dir():
                continue
            deep_skill = sub / "SKILL.md"
            if deep_skill.exists():
                parsed = _parse_frontmatter(deep_skill)
                desc = parsed.get("description", "")
                if desc:
                    return desc
    return ""


def read_submodule_configs(workspace: Path) -> list[dict[str, Any]]:
    """Read submodule configuration from .gitmodules + auto-scan.

    Returns list of ``{ path, branch, description }``.
    """
    # Step 1: Read .gitmodules metadata
    metadata: dict[str, dict[str, str]] = {}
    gitmodules = workspace / ".gitmodules"
    if gitmodules.exists():
        try:
            output = _run(
                "git config -f .gitmodules --list", cwd=str(workspace),
            )
            for line in output.split("\n"):
                m = re.match(r"^submodule\.(.+?)\.(path|branch|url)=(.*)$", line)
                if not m:
                    continue
                name, key, value = m.groups()
                metadata.setdefault(name, {})["path" if key == "path" else key] = value
        except RuntimeError:
            pass

    # Step 2: Auto-scan for initialized submodules
    initialized: list[str] = []

    def scan_dir(d: Path, rel_prefix: str = "") -> None:
        try:
            entries = sorted(d.iterdir())
        except OSError:
            return
        for entry in entries:
            if not entry.is_dir():
                continue
            name = entry.name
            if name in ("node_modules", ".git", "dist", "build"):
                continue
            rel_path = f"{rel_prefix}/{name}" if rel_prefix else name
            git_path = entry / ".git"
            if git_path.exists() and git_path.is_file():
                initialized.append(rel_path)
                continue
            if rel_path.count("/") < 2:
                scan_dir(entry, rel_path)

    scan_dir(workspace)

    # Step 3: Merge
    meta_by_path = {info.get("path", ""): info for info in metadata.values()}

    result = []
    for path in initialized:
        meta = meta_by_path.get(path, {})
        result.append({
            "path": path,
            "branch": meta.get("branch") or _get_submodule_branch(workspace, path),
            "description": meta.get("description") or _derive_submodule_description(workspace, path),
        })
    return result


# ── git helpers ────────────────────────────────────────────────────────────


def _get_remote_url(workspace: Path, submodule_path: str) -> str | None:
    full = workspace / submodule_path
    if not full.is_dir():
        return None
    try:
        url = _run("git remote get-url origin", cwd=str(full))
        return normalize_git_url(url)
    except RuntimeError:
        return None


def clear_cache(workspace: Path | None = None) -> None:
    """Clear cached registry data after workspace content changes."""
    if workspace is None:
        _GET_ALL_CACHE.clear()
        return
    _GET_ALL_CACHE.pop(str(workspace.resolve()), None)


def _get_submodule_index_ref(workspace: Path, submodule_path: str) -> str | None:
    try:
        output = _run(f"git ls-files -s -- {submodule_path}", cwd=str(workspace))
        m = re.search(r"^160000\s+([0-9a-f]+)\s+\d+\s+", output)
        if m:
            return m.group(1)
    except RuntimeError:
        pass

    try:
        output = _run(f"git ls-tree HEAD {submodule_path}", cwd=str(workspace))
        m = re.search(r"^160000\s+commit\s+([0-9a-f]+)", output)
        return m.group(1) if m else None
    except RuntimeError:
        return None


def _is_head_detached(workspace: Path, submodule_path: str) -> bool:
    full = workspace / submodule_path
    if not full.is_dir():
        return False
    try:
        _run("git symbolic-ref -q HEAD", cwd=str(full))
        return False
    except RuntimeError:
        return True


def _get_submodule_index_status(
    workspace: Path, submodule_path: str,
) -> dict[str, Any]:
    full = workspace / submodule_path
    index_ref = _get_submodule_index_ref(workspace, submodule_path)
    if not index_ref or not full.is_dir():
        return {"indexRef": index_ref, "indexAhead": 0, "indexBehind": 0, "indexDirty": False}

    # Detect uncommitted main-repo pointer changes (indexDirty)
    index_dirty = False
    try:
        st = _run(
            f"git status --porcelain {submodule_path}", cwd=str(workspace),
        )
        index_dirty = len(st) > 0
    except RuntimeError:
        pass

    try:
        commit = _run("git rev-parse --short HEAD", cwd=str(full))
        short_index = index_ref[:7]
        short_head = commit[:7] if len(commit) >= 7 else commit
        if short_index == short_head:
            return {"indexRef": index_ref, "indexAhead": 0, "indexBehind": 0, "indexDirty": index_dirty}
        full_head = _run("git rev-parse HEAD", cwd=str(full))
        counts = _run(
            f"git rev-list --left-right --count {index_ref}...{full_head}",
            cwd=str(full),
        )
        parts = counts.split()
        a = int(parts[0]) if parts else 0
        b = int(parts[1]) if len(parts) > 1 else 0
        return {"indexRef": index_ref, "indexAhead": a, "indexBehind": b, "indexDirty": index_dirty}
    except RuntimeError:
        return {"indexRef": index_ref, "indexAhead": 0, "indexBehind": 0, "indexDirty": index_dirty}


def get_submodule_status(
    workspace: Path, submodule_path: str, branch: str,
) -> dict[str, Any]:
    """Get submodule status with syncState seven states and pointer fields."""
    full = workspace / submodule_path
    if not full.is_dir():
        return {
            "commit": None, "ahead": 0, "behind": 0, "dirty": False,
            "syncState": "missing", "isDetached": False,
            "indexRef": None, "indexAhead": 0, "indexBehind": 0,
            "indexDirty": False, "checkedAt": None,
        }

    try:
        commit = _run("git rev-parse --short HEAD", cwd=str(full))
        porcelain = _run("git status --porcelain", cwd=str(full))
        dirty = len(porcelain) > 0
        detached = _is_head_detached(workspace, submodule_path)

        index_status = _get_submodule_index_status(workspace, submodule_path)
        index_ref = index_status["indexRef"]
        index_ahead = index_status["indexAhead"]
        index_behind = index_status["indexBehind"]
        index_dirty = index_status["indexDirty"]

        ahead = 0
        behind = 0
        sync_state = "synced"
        try:
            counts = _run(
                f"git rev-list --left-right --count HEAD...origin/{branch}",
                cwd=str(full),
            )
            parts = [int(x) for x in counts.split()]
            ahead = parts[0] if parts else 0
            behind = parts[1] if len(parts) > 1 else 0
            if ahead > 0 and behind > 0:
                sync_state = "diverged"
            elif ahead > 0:
                sync_state = "ahead"
            elif behind > 0:
                sync_state = "behind"
        except RuntimeError:
            sync_state = "unknown"

        if dirty and sync_state == "synced":
            sync_state = "dirty"

        return {
            "commit": commit,
            "ahead": ahead,
            "behind": behind,
            "dirty": dirty,
            "syncState": sync_state,
            "isDetached": detached,
            "indexRef": index_ref,
            "indexAhead": index_ahead,
            "indexBehind": index_behind,
            "indexDirty": index_dirty,
            "checkedAt": None,
        }
    except RuntimeError:
        return {
            "commit": None, "ahead": 0, "behind": 0, "dirty": False,
            "syncState": "missing", "isDetached": False,
            "indexRef": None, "indexAhead": 0, "indexBehind": 0,
            "indexDirty": False, "checkedAt": None,
        }


# ── getAll ─────────────────────────────────────────────────────────────────


def _get_skill_directory(skill_md_path: str) -> str:
    parts = skill_md_path.split("/")
    parts.pop()
    return "/".join(parts)


def _build_skill_item(
    workspace: Path,
    skill_md_path: str,
    parsed: dict[str, Any],
    submodule_paths: list[str] | None = None,
    remote_url_cache: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    name = parsed["name"]
    skill_dir = _get_skill_directory(skill_md_path)
    skill_type = _classify_skill_type(workspace, skill_dir)

    parent_submodule = None
    for sp in sorted(submodule_paths or [], key=len, reverse=True):
        if skill_dir == sp or skill_dir.startswith(f"{sp}/"):
            parent_submodule = sp
            break

    if parent_submodule is None:
        parts = skill_dir.split("/")
        if len(parts) >= 2 and parts[0] == "repos":
            candidate = "/".join(parts[:2])
            if (workspace / candidate / ".git").exists():
                parent_submodule = candidate

    graph_type = "isolated-skill"
    parent_node = None
    if parent_submodule:
        relative_path = skill_dir[len(parent_submodule) + 1:]
        if relative_path.startswith("skill/"):
            graph_type = "cli-skill"
            parent_node = parent_submodule
        else:
            graph_type = "repo-cli" if skill_type == "CLI" else "repo-skill"
            parent_node = parent_submodule

    def remote_url(path: str | None) -> str | None:
        if not path:
            return None
        if remote_url_cache is None:
            return None
        if path not in remote_url_cache:
            remote_url_cache[path] = _get_remote_url(workspace, path)
        return remote_url_cache[path]

    skill_root = workspace / skill_dir.replace("/", os.sep)
    file_count = _count_skill_files(skill_root) if skill_root.is_dir() else 0

    return {
        "id": name,
        "name": name,
        "description": parsed.get("description"),
        "type": skill_type,
        "graphType": graph_type,
        "parentNode": parent_node,
        "path": skill_dir,
        "skillFilePath": skill_md_path,
        "fileCount": file_count,
        "remoteUrl": remote_url(parent_submodule or skill_dir),
        "parentSkill": None,
        "isSubmodule": parent_submodule is not None,
        "submodulePath": parent_submodule,
    }


def _find_skill_lightweight(workspace: Path, skill_id: str) -> dict[str, Any] | None:
    matches: list[dict[str, Any]] = []
    for skill_md_path in _discover_skill_paths(workspace):
        full_skill_md = workspace / skill_md_path.replace("/", os.sep)
        parsed = _parse_frontmatter(full_skill_md)
        if not parsed or not parsed.get("name"):
            continue
        if parsed["name"] == skill_id:
            matches.append(_build_skill_item(workspace, skill_md_path, parsed))
    return _dedupe_skills(matches)[0] if matches else None


def _skill_priority(item: dict[str, Any]) -> tuple[int, int, str]:
    path = item.get("path") or ""
    name = item.get("name") or ""
    if path == f"skills/{name}":
        group = 0
    elif path.startswith("skills/"):
        group = 1
    elif item.get("isSubmodule"):
        group = 2
    elif path.startswith("repos/"):
        group = 3
    else:
        group = 4
    return (group, path.count("/"), path)


def _dedupe_skills(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for item in items:
        name = item["name"]
        current = selected.get(name)
        if current is None or _skill_priority(item) < _skill_priority(current):
            selected[name] = item
    return sorted(selected.values(), key=lambda item: item["name"].lower())


def get_all(workspace: Path, *, force: bool = False) -> dict[str, Any]:
    """Return ``{ skills, repoNodes, submodules, relationships, generatedAt }``.

    This is the frozen contract from skill-registry.js getAll().
    """
    workspace = workspace.resolve()
    cache_key = str(workspace)
    now = time.monotonic()
    if not force:
        cached = _GET_ALL_CACHE.get(cache_key)
        if cached and now - cached[0] <= _CACHE_TTL_SECONDS:
            return cached[1]

    submodule_configs = read_submodule_configs(workspace)
    submodule_paths = [s["path"] for s in submodule_configs]
    remote_url_cache: dict[str, str | None] = {}

    def remote_url(path: str | None) -> str | None:
        if not path:
            return None
        if path not in remote_url_cache:
            remote_url_cache[path] = _get_remote_url(workspace, path)
        return remote_url_cache[path]

    submodules = []
    for sub in submodule_configs:
        status = get_submodule_status(workspace, sub["path"], sub["branch"])
        submodules.append({
            "path": sub["path"],
            "branch": sub["branch"],
            "description": sub["description"],
            "remoteUrl": remote_url(sub["path"]),
            "status": status,
        })

    skill_paths = _discover_skill_paths(workspace)
    discovered_skills: list[dict[str, Any]] = []

    for skill_md_path in skill_paths:
        full_skill_md = workspace / skill_md_path.replace("/", os.sep)
        parsed = _parse_frontmatter(full_skill_md)
        if not parsed or not parsed.get("name"):
            continue
        skill = _build_skill_item(
            workspace,
            skill_md_path,
            parsed,
            submodule_paths,
            remote_url_cache,
        )
        discovered_skills.append(skill)

    skills = _dedupe_skills(discovered_skills)
    relationships: list[dict[str, str]] = []
    for skill in skills:
        if skill["submodulePath"] and skill["path"] != skill["submodulePath"]:
            relationships.append({
                "from": skill["submodulePath"], "to": skill["name"], "type": "contains",
            })

    # Synthesize repo root nodes
    repo_nodes = []
    for sub in submodules:
        child_skills = [s for s in skills if s["submodulePath"] == sub["path"]]
        if not child_skills:
            continue
        is_cli_repo = _classify_skill_type(workspace, sub["path"]) == "CLI"
        graph_type = "repo-cli" if is_cli_repo else "repo-skill"
        # NOTE: ntdev DEBUG residual intentionally NOT ported
        repo_nodes.append({
            "id": sub["path"],
            "name": sub["path"].removeprefix("repos/"),
            "description": sub["description"],
            "type": graph_type,
            "graphType": graph_type,
            "parentNode": None,
            "path": sub["path"],
            "skillFilePath": None,
            "fileCount": 0,
            "remoteUrl": sub["remoteUrl"],
            "parentSkill": None,
            "isSubmodule": True,
            "submodulePath": sub["path"],
            "isSubmoduleRoot": True,
            "branch": sub["branch"],
        })

    relationships.extend(_KNOWN_DEPENDENCIES)

    result = {
        "skills": skills,
        "repoNodes": repo_nodes,
        "submodules": submodules,
        "relationships": relationships,
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
    }
    _GET_ALL_CACHE[cache_key] = (now, result)
    return result


def get_skill(workspace: Path, skill_id: str) -> dict[str, Any] | None:
    """Get a single skill by id/name."""
    if not skill_id:
        return None
    workspace = workspace.resolve()
    cached = _GET_ALL_CACHE.get(str(workspace))
    if cached and time.monotonic() - cached[0] <= _CACHE_TTL_SECONDS:
        for s in cached[1]["skills"]:
            if s["id"] == skill_id or s["name"] == skill_id:
                return s
    lightweight = _find_skill_lightweight(workspace, skill_id)
    if lightweight:
        return lightweight
    data = get_all(workspace)
    for s in data["skills"]:
        if s["id"] == skill_id or s["name"] == skill_id:
            return s
    return None
