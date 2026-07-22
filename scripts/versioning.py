#!/usr/bin/env python3
"""Version helpers for skillreg release metadata."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11.
    tomllib = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
RUNTIME_INIT = ROOT / "src" / "skillreg" / "__init__.py"
BUILTIN_SKILL = ROOT / "src" / "skillreg" / "builtin" / "skillreg-skill" / "SKILL.md"
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def read_pyproject_version(root: Path = ROOT) -> str:
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    if tomllib is None:
        return read_pyproject_version_fallback(text)
    data: dict[str, Any] = tomllib.loads(text)
    return str(data["project"]["version"])


def read_pyproject_version_fallback(text: str) -> str:
    in_project = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "[project]":
            in_project = True
            continue
        if in_project and stripped.startswith("["):
            break
        if not in_project or not stripped.startswith("version"):
            continue
        match = re.match(r'^version\s*=\s*"([^"]+)"\s*$', stripped)
        if match:
            return match.group(1)
    raise RuntimeError("pyproject.toml must define [project].version")


def read_runtime_version(root: Path = ROOT) -> str:
    init_path = root / "src" / "skillreg" / "__init__.py"
    tree = ast.parse(init_path.read_text(encoding="utf-8"), filename=str(init_path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets):
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return node.value.value
    raise RuntimeError("src/skillreg/__init__.py must define string __version__")


def read_builtin_skill_version(root: Path = ROOT) -> str:
    text = _builtin_skill_path(root).read_text(encoding="utf-8")
    frontmatter = _frontmatter(text)
    match = re.search(r'(?m)^  version:\s*"([^"]+)"\s*$', frontmatter)
    if not match:
        raise RuntimeError("builtin skill must define metadata.version")
    return match.group(1)


def read_npm_package_version(root: Path = ROOT) -> str:
    data = json.loads((root / "npm" / "package.json").read_text(encoding="utf-8"))
    return str(data["version"])


def read_npm_lock_versions(root: Path = ROOT) -> tuple[str, str]:
    data = json.loads((root / "npm" / "package-lock.json").read_text(encoding="utf-8"))
    return str(data["version"]), str(data["packages"][""]["version"])


def sync_version(version: str, root: Path = ROOT) -> None:
    validate_release_version(version)
    _replace_pyproject_version(version, root)
    _replace_runtime_version(version, root)
    _replace_builtin_skill_version(version, root)
    _replace_npm_versions(version, root)


def bump_version_for_message(current: str, message: str) -> str:
    validate_release_version(current)
    _major, minor, patch = [int(part) for part in current.split(".")]
    major = 1
    if _is_feat_commit(message):
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def bump_from_commit_message(commit_msg_file: Path, root: Path = ROOT) -> str:
    current = read_pyproject_version(root)
    message = commit_msg_file.read_text(encoding="utf-8")
    next_version = bump_version_for_message(current, message)
    sync_version(next_version, root)
    return next_version


def check_versions(root: Path = ROOT, require_tag: bool = False) -> list[str]:
    pyproject_version = read_pyproject_version(root)
    runtime_version = read_runtime_version(root)
    builtin_version = read_builtin_skill_version(root)
    npm_version = read_npm_package_version(root)
    npm_lock_version, npm_lock_root_version = read_npm_lock_versions(root)
    errors: list[str] = []

    if not VERSION_RE.match(pyproject_version):
        errors.append(f"pyproject version must be x.y.z: {pyproject_version}")
    if runtime_version != pyproject_version:
        errors.append(
            "__version__ mismatch: "
            f"src/skillreg/__init__.py has {runtime_version}, "
            f"pyproject.toml has {pyproject_version}"
        )
    if builtin_version != pyproject_version:
        errors.append(
            "builtin skill version mismatch: "
            f"SKILL.md has {builtin_version}, pyproject.toml has {pyproject_version}"
        )
    if npm_version != pyproject_version:
        errors.append(
            "npm package version mismatch: "
            f"npm/package.json has {npm_version}, pyproject.toml has {pyproject_version}"
        )
    if npm_lock_version != pyproject_version or npm_lock_root_version != pyproject_version:
        errors.append(
            "npm lock version mismatch: "
            f"npm/package-lock.json has {npm_lock_version}/{npm_lock_root_version}, "
            f"pyproject.toml has {pyproject_version}"
        )

    if require_tag:
        tag = tag_from_env()
        expected = f"v{pyproject_version}"
        if tag != expected:
            errors.append(f"tag mismatch: expected {expected}, got {tag or '(none)'}")

    return errors


def validate_release_version(version: str) -> None:
    if not VERSION_RE.match(version):
        raise ValueError(f"version must be x.y.z: {version}")


def tag_from_env() -> str | None:
    ref_name = os.environ.get("GITHUB_REF_NAME")
    if ref_name:
        return ref_name
    ref = os.environ.get("GITHUB_REF")
    if ref and ref.startswith("refs/tags/"):
        return ref.removeprefix("refs/tags/")
    return None


def current_branch(root: Path = ROOT) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _is_feat_commit(message: str) -> bool:
    for line in message.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        return bool(re.match(r"^feat(?:\([^)]+\))?!?:", stripped))
    return False


def _replace_pyproject_version(version: str, root: Path) -> None:
    path = root / "pyproject.toml"
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(r'(?m)^version\s*=\s*"[^"]+"\s*$')
    updated, count = pattern.subn(f'version = "{version}"', text, count=1)
    if count != 1:
        raise RuntimeError("failed to update pyproject version")
    path.write_text(updated, encoding="utf-8")


def _replace_runtime_version(version: str, root: Path) -> None:
    path = root / "src" / "skillreg" / "__init__.py"
    text = path.read_text(encoding="utf-8")
    updated, count = re.subn(
        r'(?m)^__version__\s*=\s*"[^"]+"\s*$',
        f'__version__ = "{version}"',
        text,
        count=1,
    )
    if count != 1:
        raise RuntimeError("failed to update runtime version")
    path.write_text(updated, encoding="utf-8")


def _replace_builtin_skill_version(version: str, root: Path) -> None:
    path = _builtin_skill_path(root)
    text = path.read_text(encoding="utf-8")
    frontmatter = _frontmatter(text)
    if re.search(r"(?m)^metadata:\s*$", frontmatter):
        updated, count = re.subn(
            r'(?m)^  version:\s*"[^"]+"\s*$',
            f'  version: "{version}"',
            text,
            count=1,
        )
        if count == 0:
            updated = re.sub(
                r"(?m)^metadata:\s*$",
                f'metadata:\n  version: "{version}"',
                text,
                count=1,
            )
    else:
        updated = text.replace(
            "\n---\n",
            f'\nmetadata:\n  version: "{version}"\n---\n',
            1,
        )
    path.write_text(updated, encoding="utf-8")


def _replace_npm_versions(version: str, root: Path) -> None:
    package_path = root / "npm" / "package.json"
    package_data = json.loads(package_path.read_text(encoding="utf-8"))
    package_data["version"] = version
    package_path.write_text(json.dumps(package_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lock_path = root / "npm" / "package-lock.json"
    lock_data = json.loads(lock_path.read_text(encoding="utf-8"))
    lock_data["version"] = version
    lock_data["packages"][""]["version"] = version
    lock_path.write_text(json.dumps(lock_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _builtin_skill_path(root: Path) -> Path:
    return root / "src" / "skillreg" / "builtin" / "skillreg-skill" / "SKILL.md"


def _frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        raise RuntimeError("builtin SKILL.md must start with YAML frontmatter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise RuntimeError("builtin SKILL.md frontmatter is not closed")
    return parts[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage skillreg versions.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check", help="Check version consistency.")
    check_parser.add_argument("--require-tag", action="store_true")

    subparsers.add_parser("current", help="Print the current pyproject version.")

    sync_parser = subparsers.add_parser("sync", help="Sync all version metadata.")
    sync_parser.add_argument("--version", help="Version to write. Defaults to pyproject version.")

    bump_parser = subparsers.add_parser("bump", help="Bump version from a commit message.")
    bump_parser.add_argument("--commit-msg-file", required=True, type=Path)
    bump_parser.add_argument("--branch", default=None)

    args = parser.parse_args()

    if args.command == "check":
        errors = check_versions(require_tag=args.require_tag)
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print(f"version ok: {read_pyproject_version()}")
        return 0

    if args.command == "current":
        print(read_pyproject_version())
        return 0

    if args.command == "sync":
        version = args.version or read_pyproject_version()
        sync_version(version)
        print(f"version synced: {version}")
        return 0

    if args.command == "bump":
        branch = args.branch or current_branch()
        if branch != "main":
            print(f"version bump skipped on branch: {branch or '(unknown)'}")
            return 0
        next_version = bump_from_commit_message(args.commit_msg_file)
        print(f"version bumped: {next_version}")
        return 0

    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
