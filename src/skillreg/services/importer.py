"""Import service — ported from agent-hub ``importer.js``.

Handles three import sources (zip / git-clone / local directory) × two modes
(skill copy / submodule add), plus update preview/execute.
"""

from __future__ import annotations

import io
import re
import shutil
import subprocess
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Any

from ..config import load_config

# ── constants ──────────────────────────────────────────────────────────────

_SKILL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")

# Files/dirs excluded during copy
_COPY_IGNORED_DIRS = frozenset({"__pycache__", "__MACOSX"})
_COPY_IGNORED_PREFIXES = (".",)  # except .gitignore


def _is_valid_skill_name(name: str) -> bool:
    return bool(_SKILL_NAME_RE.match(name))


def _resolve_workspace() -> Path:
    """Resolve and validate the configured workspace path."""
    cfg = load_config()
    if not cfg.workspace_path:
        raise ValueError("Workspace not configured")
    ws = Path(cfg.workspace_path).expanduser().resolve()
    if not ws.is_dir():
        raise ValueError(f"Workspace directory not found: {ws}")
    return ws


# ── workspace creation ─────────────────────────────────────────────────────


def create_workspace(location: str) -> dict:
    """Create a new workspace at the given location.

    - ``git init``
    - Create ``skills/``, ``repos/`` directories
    - Write ``.gitignore`` (including ``.skillreg/builtin/``)
    - Write ``README.md``
    - Update ``~/.skillreg/config.json`` workspace pointer
    """
    ws = Path(location).expanduser().resolve()
    if ws.exists() and any(ws.iterdir()):
        raise ValueError(f"Directory not empty: {ws}")

    ws.mkdir(parents=True, exist_ok=True)
    (ws / "skills").mkdir(exist_ok=True)
    (ws / "repos").mkdir(exist_ok=True)

    # .gitignore
    (ws / ".gitignore").write_text(
        "# skillreg workspace\n"
        ".skillreg/builtin/\n",
        encoding="utf-8",
    )

    # README
    (ws / "README.md").write_text(
        f"# skillreg workspace\n\n"
        f"Skills managed by [skillreg](https://github.com/fcraft/skillreg).\n\n"
        f"- `skills/` — individual skills\n"
        f"- `repos/` — submodule-based skills\n",
        encoding="utf-8",
    )

    # git init
    try:
        subprocess.run(
            ["git", "init"], cwd=str(ws), capture_output=True, text=True, check=True,
        )
        subprocess.run(
            ["git", "add", "-A"], cwd=str(ws), capture_output=True, text=True, check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "chore: init skillreg workspace"],
            cwd=str(ws), capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError as e:
        raise ValueError(f"git init failed: {e.stderr.strip()}")

    # Update config
    cfg = load_config()
    cfg.workspace_path = str(ws)
    from ..config import save_config
    save_config(cfg)

    return {
        "workspace_path": str(ws),
        "has_git": (ws / ".git").exists(),
        "has_skills_dir": (ws / "skills").is_dir(),
        "has_repos_dir": (ws / "repos").is_dir(),
    }


# ── import validation ─────────────────────────────────────────────────────


def validate_import_source(source_path: str) -> dict:
    """Validate an import source directory.

    Returns ``{ valid, skillName, description, fileCount, conflict }``.
    """
    src = Path(source_path).expanduser().resolve()
    if not src.exists():
        return {"valid": False, "error": f"source path does not exist: {source_path}"}
    if not src.is_dir():
        return {"valid": False, "error": f"source path is not a directory: {source_path}"}

    skill_md = src / "SKILL.md"
    if not skill_md.exists():
        return {"valid": False, "error": "No SKILL.md found in source directory"}

    from .skill_registry import _parse_frontmatter
    fm = _parse_frontmatter(skill_md)
    name = fm.get("name") if fm else None
    if not name:
        return {"valid": False, "error": "SKILL.md frontmatter must contain a name field"}

    if not _is_valid_skill_name(name):
        return {"valid": False, "error": f"Invalid skill name '{name}': must match [A-Za-z0-9][A-Za-z0-9_-]*"}

    file_count = _count_import_files(src)

    ws = _resolve_workspace()
    target_dir = ws / "skills" / name
    conflict = target_dir.exists()

    return {
        "valid": True,
        "skillName": name,
        "description": fm.get("description", ""),
        "fileCount": file_count,
        "conflict": {
            "exists": conflict,
            "existingPath": f"skills/{name}" if conflict else None,
        },
    }


def _count_import_files(directory: Path) -> int:
    count = 0
    for entry in directory.rglob("*"):
        if entry.name.startswith(".") and entry.name != ".gitignore":
            continue
        if entry.name.startswith("._"):
            continue
        if entry.is_dir():
            if entry.name in _COPY_IGNORED_DIRS:
                continue
        elif entry.is_file():
            count += 1
    return count


# ── zip extraction ────────────────────────────────────────────────────────


def extract_zip(buffer: bytes) -> dict:
    """Extract a zip buffer to a temp directory.

    Returns ``{ tempPath, extractedRoot }`` where extractedRoot is the
    shallowest directory containing SKILL.md.
    """
    uid = uuid.uuid4().hex
    temp_path = Path(tempfile.gettempdir()) / f"skillreg-import-{uid}"

    try:
        with zipfile.ZipFile(io.BytesIO(buffer)) as zf:
            zf.extractall(temp_path)

        extracted_root = _find_skill_md_dir(temp_path)
        return {"tempPath": str(temp_path), "extractedRoot": str(extracted_root)}
    except Exception:
        shutil.rmtree(temp_path, ignore_errors=True)
        raise


def _find_skill_md_dir(root: Path) -> Path:
    """BFS to find shallowest directory containing SKILL.md."""
    if (root / "SKILL.md").exists():
        return root
    queue = [root]
    while queue:
        current = queue.pop(0)
        try:
            entries = sorted(current.iterdir())
        except OSError:
            continue
        for entry in entries:
            if not entry.is_dir():
                continue
            if entry.name.startswith(".") or entry.name == "__MACOSX":
                continue
            if (entry / "SKILL.md").exists():
                return entry
            queue.append(entry)
    return root


# ── skill import (copy mode) ─────────────────────────────────────────────


def import_skill(
    source_path: str,
    temp_path: str | None = None,
    rename_to: str | None = None,
    force: bool = False,
) -> dict:
    """Import a skill by copying files to ``skills/<name>/``."""
    src = Path(source_path).expanduser().resolve()
    ws = _resolve_workspace()

    # Validate
    skill_md = src / "SKILL.md"
    if not skill_md.exists():
        raise ValueError(f"No SKILL.md found in {source_path}")

    from .skill_registry import _parse_frontmatter
    fm = _parse_frontmatter(skill_md)
    name = rename_to or fm.get("name")
    if not name:
        raise ValueError("SKILL.md frontmatter must contain a name field")
    if not _is_valid_skill_name(name):
        raise ValueError(f"Invalid skill name: {name}")

    target_dir = ws / "skills" / name
    if target_dir.exists():
        if not force:
            raise ValueError(f"Skill '{name}' already exists at skills/{name}")
        shutil.rmtree(target_dir)

    files_copied = _copy_skill_files(src, target_dir)

    # Git commit in workspace
    _git_add_commit(ws, f"skills/{name}", f"skillreg: register '{name}'")

    # Cleanup temp
    if temp_path:
        cleanup_temp(temp_path)

    commit = _get_head_commit(ws)
    return {"name": name, "skillPath": f"skills/{name}", "commit": commit, "filesCopied": files_copied}


def _copy_skill_files(src: Path, dst: Path) -> int:
    """Copy skill files, skipping hidden/ignored. Returns count."""
    count = 0
    dst.mkdir(parents=True, exist_ok=True)
    for entry in src.iterdir():
        if entry.is_dir():
            if entry.name in _COPY_IGNORED_DIRS or entry.name.startswith("."):
                continue
            count += _copy_skill_files(entry, dst / entry.name)
        elif entry.is_file():
            if entry.name.startswith(".") and entry.name != ".gitignore":
                continue
            if entry.name.startswith("._"):
                continue
            (dst / entry.name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(entry, dst / entry.name)
            count += 1
    return count


# ── update preview/execute ──────────────────────────────────────────────


def preview_update(source_path: str, skill_name: str) -> dict:
    """Compare source directory with existing skill, returning file-level diff."""
    src = Path(source_path).expanduser().resolve()
    ws = _resolve_workspace()
    target_dir = ws / "skills" / skill_name

    if not src.exists():
        raise ValueError(f"Source path does not exist: {source_path}")
    if not target_dir.exists():
        raise ValueError(f"Skill '{skill_name}' does not exist at skills/{skill_name}")

    src_files = _build_file_map(src)
    target_files = _build_file_map(target_dir)

    all_paths = set(src_files) | set(target_files)
    files = []
    unchanged = added = modified = removed = 0

    for rel_path in sorted(all_paths):
        in_src = rel_path in src_files
        in_target = rel_path in target_files

        if in_src and in_target:
            if src_files[rel_path] == target_files[rel_path]:
                unchanged += 1
                files.append({"path": rel_path, "status": "unchanged"})
            else:
                modified += 1
                files.append({"path": rel_path, "status": "modified"})
        elif in_src:
            added += 1
            files.append({"path": rel_path, "status": "added"})
        else:
            removed += 1
            files.append({"path": rel_path, "status": "removed"})

    # Sort: modified → added → removed → unchanged
    order = {"modified": 0, "added": 1, "removed": 2, "unchanged": 3}
    files.sort(key=lambda f: (order.get(f["status"], 4), f["path"]))

    return {"summary": {"unchanged": unchanged, "added": added, "modified": modified, "removed": removed}, "files": files}


def execute_update(source_path: str, skill_name: str, temp_path: str | None = None) -> dict:
    """Execute a skill update (overwrite with new source)."""
    return import_skill(source_path, temp_path, rename_to=skill_name, force=True)


def convert_skill(name: str) -> dict:
    """Convert ``skills/<name>`` into ``repos/<name>-cli/skill/<name>``."""
    if not name:
        raise ValueError("missing name parameter")
    if not _is_valid_skill_name(name):
        raise ValueError(
            f"invalid skill name '{name}': must match [A-Za-z0-9][A-Za-z0-9_-]*"
        )

    ws = _resolve_workspace()
    source_skill_dir = ws / "skills" / name
    if not source_skill_dir.exists():
        raise FileNotFoundError(f"skill '{name}' not found at skills/{name}")

    skill_md = source_skill_dir / "SKILL.md"
    if not skill_md.exists():
        raise ValueError(f"no SKILL.md found for skill '{name}'")

    repo_name = f"{name}-cli"
    target_repo_dir = ws / "repos" / repo_name
    if target_repo_dir.exists():
        raise FileExistsError(f"repo already exists at repos/{repo_name}")

    from .skill_registry import _parse_frontmatter

    frontmatter = _parse_frontmatter(skill_md) or {}
    version = str(frontmatter.get("version") or "0.1.0")
    description = str(frontmatter.get("description") or f"{name} skill")

    src_dir = target_repo_dir / "src" / f"{name.replace('-', '_')}_cli"
    src_dir.mkdir(parents=True, exist_ok=True)

    (target_repo_dir / "pyproject.toml").write_text(
        "[build-system]\n"
        'requires = ["hatchling"]\n'
        'build-backend = "hatchling.build"\n'
        "\n"
        "[project]\n"
        f'name = "{repo_name}"\n'
        f'version = "{version}"\n'
        f'description = "{description}"\n'
        'requires-python = ">=3.8"\n'
        "\n"
        "[project.scripts]\n"
        f'{name} = "{name.replace("-", "_")}_cli.main:main"\n',
        encoding="utf-8",
    )

    (target_repo_dir / ".gitignore").write_text(
        "__pycache__/\n"
        "*.egg-info/\n"
        "dist/\n"
        "build/\n"
        "*.pyc\n"
        "*.pyo\n"
        ".DS_Store\n",
        encoding="utf-8",
    )

    (src_dir / "__init__.py").write_text(
        f'__version__ = "{version}"\n',
        encoding="utf-8",
    )
    module_name = f"{name.replace('-', '_')}_cli"
    (src_dir / "main.py").write_text(
        f'"""CLI entry point for {name}."""\n'
        "import argparse\n"
        "import sys\n"
        "\n"
        "\n"
        "def main():\n"
        "    parser = argparse.ArgumentParser(\n"
        f'        prog="{name}",\n'
        f'        description="{description}",\n'
        "    )\n"
        "    parser.add_argument(\n"
        '        "--version",\n'
        '        action="version",\n'
        f'        version=f"%(prog)s {{__import__(\"{module_name}\").__version__}}",\n'
        "    )\n"
        "    parser.parse_args()\n"
        f'    print("TODO: implement {name} CLI", file=sys.stderr)\n'
        "    return 1\n"
        "\n"
        "\n"
        'if __name__ == "__main__":\n'
        "    sys.exit(main())\n",
        encoding="utf-8",
    )

    skill_target_dir = target_repo_dir / "skill" / name
    skill_target_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        source_skill_dir.rename(skill_target_dir)
    except OSError:
        _copy_skill_files(source_skill_dir, skill_target_dir)
        shutil.rmtree(source_skill_dir)

    try:
        subprocess.run(
            ["git", "init"],
            cwd=str(target_repo_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        subprocess.run(
            ["git", "add", "-A"],
            cwd=str(target_repo_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", f"init: {name} skill (converted from skills/)"],
            cwd=str(target_repo_dir),
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        pass

    return {
        "name": name,
        "repoPath": f"repos/{repo_name}",
        "skillPath": f"repos/{repo_name}/skill/{name}",
    }


# ── git import ──────────────────────────────────────────────────────────


def git_clone_to_temp(url: str, branch: str | None = None) -> dict:
    """Clone a git repo (depth 1) to temp and discover skills."""
    uid = uuid.uuid4().hex
    temp_path = Path(tempfile.gettempdir()) / f"skillreg-git-{uid}"

    args = ["git", "clone", "--depth", "1"]
    if branch:
        args.extend(["--branch", branch])
    args.extend([url, str(temp_path)])

    try:
        subprocess.run(args, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        shutil.rmtree(temp_path, ignore_errors=True)
        raise ValueError(f"Git clone failed: {e.stderr.strip()}")

    skills = _discover_skills_in_dir(temp_path)
    if not skills:
        shutil.rmtree(temp_path, ignore_errors=True)
        raise ValueError("No SKILL.md found in the cloned repository")

    return {"tempPath": str(temp_path), "skills": skills}


def _discover_skills_in_dir(root: Path) -> list[dict]:
    """Find skills in a directory tree (returns list of {name, description, dirName, relPath})."""
    from .skill_registry import _parse_frontmatter

    results: list[dict] = []

    def visit(d: Path) -> None:
        skill_md = d / "SKILL.md"
        if skill_md.exists():
            fm = _parse_frontmatter(skill_md)
            if fm and fm.get("name"):
                rel = str(d.relative_to(root)) if d != root else "."
                results.append({
                    "name": fm["name"],
                    "description": fm.get("description", ""),
                    "dirName": d.name,
                    "relPath": rel,
                })
        for entry in sorted(d.iterdir()):
            if not entry.is_dir():
                continue
            if entry.name.startswith(".") or entry.name in ("__MACOSX", "__pycache__"):
                continue
            visit(entry)

    visit(root)
    return results


def git_import_skills(
    temp_path: str,
    selected_skills: list[str],
    target_dir: str = "",
) -> dict:
    """Import selected skills from a cloned repo (copy mode)."""
    temp = Path(temp_path)
    if not temp.exists():
        raise ValueError(f"Temp path does not exist: {temp_path}")

    ws = _resolve_workspace()
    normalized = target_dir.strip("/")
    skills_base = ws / "skills" / normalized if normalized else ws / "skills"
    skills_base.mkdir(parents=True, exist_ok=True)

    all_skills = _discover_skills_in_dir(temp)
    imported = []

    for skill_name in selected_skills:
        match = next((s for s in all_skills if s["name"] == skill_name), None)
        if not match:
            raise ValueError(f"Skill '{skill_name}' not found in cloned repo")
        if not _is_valid_skill_name(skill_name):
            raise ValueError(f"Invalid skill name: {skill_name}")

        src_dir = temp if match["relPath"] == "." else temp / match["relPath"]
        target_skill_dir = skills_base / skill_name
        if target_skill_dir.exists():
            raise ValueError(f"Skill '{skill_name}' already exists")

        files_copied = _copy_skill_files(src_dir, target_skill_dir)
        imported.append({
            "name": skill_name,
            "skillPath": f"skills/{normalized + '/' if normalized else ''}{skill_name}",
            "filesCopied": files_copied,
        })

    # Git commit
    changed = " ".join(f"skills/{normalized + '/' if normalized else ''}{s}" for s in selected_skills)
    _git_add_commit(ws, changed, f"skillreg: import {len(imported)} skill(s) from git")

    cleanup_temp(temp_path)
    commit = _get_head_commit(ws)
    target_path = f"skills/{normalized}" if normalized else "skills"
    return {"imported": imported, "targetPath": target_path, "commit": commit}


def git_import_as_submodule(
    url: str,
    target_path: str,
    branch: str | None = None,
) -> dict:
    """Add a git repo as a submodule to ``repos/``."""
    ws = _resolve_workspace()
    full_path = ws / target_path
    if full_path.exists():
        raise ValueError(f"Target path already exists: {target_path}")

    args = ["git", "submodule", "add"]
    if branch:
        args.extend(["-b", branch])
    args.extend([url, target_path])

    try:
        subprocess.run(args, cwd=str(ws), capture_output=True, text=True, check=True)
        _git_add_commit(ws, f"{target_path} .gitmodules", f"skillreg: add submodule '{target_path}'")
    except subprocess.CalledProcessError as e:
        shutil.rmtree(full_path, ignore_errors=True)
        raise ValueError(f"Submodule add failed: {e.stderr.strip()}")

    commit = _get_head_commit(ws)
    return {"submodulePath": target_path, "url": url, "branch": branch or "main", "commit": commit}


# ── temp cleanup ─────────────────────────────────────────────────────────


def cleanup_temp(temp_path: str) -> None:
    """Remove a temp directory (safety: must be under tempdir)."""
    if not temp_path:
        return
    p = Path(temp_path).resolve()
    tmp = Path(tempfile.gettempdir()).resolve()
    if not str(p).startswith(str(tmp)):
        raise ValueError("cleanup_temp: path is not in tmpdir")
    shutil.rmtree(p, ignore_errors=True)


# ── helpers ─────────────────────────────────────────────────────────────


def _build_file_map(directory: Path) -> dict[str, str]:
    """Build SHA256 hash map of files in a directory (rel_path → hexdigest)."""
    import hashlib

    result: dict[str, str] = {}

    def walk(base: Path, rel_prefix: str = ""):
        try:
            entries = sorted(base.iterdir())
        except OSError:
            return
        for entry in entries:
            if entry.is_dir():
                if entry.name in _COPY_IGNORED_DIRS or entry.name.startswith("."):
                    continue
                child_rel = f"{rel_prefix}/{entry.name}" if rel_prefix else entry.name
                walk(entry, child_rel)
            elif entry.is_file():
                if entry.name.startswith(".") and entry.name != ".gitignore":
                    continue
                if entry.name.startswith("._"):
                    continue
                file_rel = f"{rel_prefix}/{entry.name}" if rel_prefix else entry.name
                try:
                    h = hashlib.sha256(entry.read_bytes()).hexdigest()
                except OSError:
                    h = ""
                result[file_rel] = h

    walk(directory)
    return result


def _git_add_commit(ws: Path, paths: str, message: str) -> None:
    """Run git add + commit in workspace (non-fatal on failure)."""
    try:
        subprocess.run(
            ["git", "add", *paths.split()],
            cwd=str(ws), capture_output=True, text=True, check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(ws), capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError:
        pass  # Nothing to commit is OK


def _get_head_commit(ws: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ws), capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None
