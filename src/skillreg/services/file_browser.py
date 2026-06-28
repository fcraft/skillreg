"""File browser service — ported from agent-hub ``file-browser.js``.

Provides file tree building and file content reading with safety guards.
Deep: 4, nodes: 300, cache: 30s, preview: 100KB.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

_MAX_TREE_DEPTH = 4
_MAX_TREE_NODES = 300
_MAX_PREVIEW_BYTES = 100 * 1024

_IGNORED_TREE_DIRS = frozenset({
    ".git", "node_modules", ".venv", "venv",
    "__pycache__", "dist", "build", "coverage",
})

_LANGUAGE_MAP = {
    ".md": "markdown",
    ".json": "json",
    ".js": "javascript",
    ".mjs": "javascript",
    ".ts": "typescript",
    ".vue": "vue",
    ".py": "python",
    ".sh": "shell",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".toml": "toml",
    ".css": "css",
    ".html": "html",
}

_tree_cache: dict[str, tuple[float, dict]] = {}
_TREE_CACHE_TTL = 30  # seconds


def build_tree(root: str = ".") -> dict[str, Any] | None:
    """Build a file tree starting from root (relative to workspace).

    Returns a tree node: ``{ name, path, type, children? }``.
    Depth limited to 4, nodes to 300. Cached for 30s.
    """
    ws = _get_workspace()
    base = (ws / root).resolve() if root != "." else ws.resolve()
    if not _is_inside(ws.resolve(), base):
        return None

    cache_key = str(base)
    now = time.time()
    if cache_key in _tree_cache:
        ts, cached = _tree_cache[cache_key]
        if now - ts < _TREE_CACHE_TTL:
            return cached

    node_count = 0

    def visit(current: Path, depth: int) -> dict | None:
        nonlocal node_count
        if node_count >= _MAX_TREE_NODES:
            return None
        node_count += 1

        rel = str(current.relative_to(base)) if current != base else ""
        node: dict = {
            "name": current.name if current != base else ".",
            "path": rel.replace("\\", "/"),
            "type": "dir",
        }

        if depth >= _MAX_TREE_DEPTH:
            return node

        children = []
        try:
            entries = sorted(current.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        except OSError:
            return node

        for entry in entries:
            if entry.is_dir():
                if entry.name in _IGNORED_TREE_DIRS or entry.name.startswith("."):
                    continue
                child = visit(entry, depth + 1)
                if child:
                    children.append(child)
            elif entry.is_file():
                if node_count >= _MAX_TREE_NODES:
                    break
                node_count += 1
                children.append({
                    "name": entry.name,
                    "path": str(entry.relative_to(base)).replace("\\", "/"),
                    "type": "file",
                })

        if children:
            node["children"] = children
        return node

    result = visit(base, 0)
    if result:
        _tree_cache[cache_key] = (now, result)
    return result


def read_file_content(root: str, rel_path: str) -> dict:
    """Read file content with safety guards.

    Returns ``{ content, language, size }`` for text files,
    or ``{ binary: true, size }`` for binary files.
    """
    ws = _get_workspace()
    base = (ws / root).resolve() if root != "." else ws.resolve()

    # Path traversal guard
    if not rel_path or rel_path.startswith("/") or ".." in rel_path.split("/"):
        raise ValueError("Invalid file path")

    file_path = (base / rel_path).resolve()
    if not _is_inside(base, file_path):
        raise PermissionError("File is outside base directory")

    if not file_path.is_file():
        raise ValueError("Path is not a file")

    stat = file_path.stat()
    if stat.st_size > _MAX_PREVIEW_BYTES:
        raise FileTooLargeError(stat.st_size)

    try:
        raw = file_path.read_bytes()
    except OSError as e:
        raise ValueError(f"Cannot read file: {e}")

    if _is_binary(raw):
        return {"binary": True, "size": len(raw)}

    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        return {"binary": True, "size": len(raw)}

    return {
        "content": content,
        "language": _language_for_path(file_path.name),
        "size": len(raw),
    }


def clear_cache() -> None:
    """Clear the tree cache."""
    _tree_cache.clear()


# ── helpers ─────────────────────────────────────────────────────────────


class FileTooLargeError(ValueError):
    def __init__(self, size: int):
        self.size = size
        super().__init__("File is too large to preview")


def _get_workspace() -> Path:
    from ..config import load_config
    cfg = load_config()
    if not cfg.workspace_path:
        raise ValueError("Workspace not configured")
    return Path(cfg.workspace_path).expanduser().resolve()


def _is_inside(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _language_for_path(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return _LANGUAGE_MAP.get(ext, "text")


def _is_binary(data: bytes) -> bool:
    if b"\x00" in data:
        return True
    sample = data[:512]
    if len(sample) == 0:
        return False
    suspicious = sum(1 for b in sample if b < 7 or (14 < b < 32))
    return suspicious / len(sample) > 0.3
