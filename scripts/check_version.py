#!/usr/bin/env python3
"""Validate skillreg release version consistency.

The human-edited source of truth is ``pyproject.toml``. This script checks
that the package runtime version and, during tag builds, the Git tag agree.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import sys
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.9/3.10.
    tomllib = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?(?:\.post\d+)?(?:\.dev\d+)?$")


def read_pyproject_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
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


def read_runtime_version() -> str:
    init_path = ROOT / "src" / "skillreg" / "__init__.py"
    tree = ast.parse(init_path.read_text(encoding="utf-8"), filename=str(init_path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets):
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return node.value.value
    raise RuntimeError("src/skillreg/__init__.py must define string __version__")


def tag_from_env() -> str | None:
    ref_name = os.environ.get("GITHUB_REF_NAME")
    if ref_name:
        return ref_name
    ref = os.environ.get("GITHUB_REF")
    if ref and ref.startswith("refs/tags/"):
        return ref.removeprefix("refs/tags/")
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-tag",
        action="store_true",
        help="Also require the current GitHub tag to equal v<pyproject version>.",
    )
    args = parser.parse_args()

    pyproject_version = read_pyproject_version()
    runtime_version = read_runtime_version()
    errors: list[str] = []

    if not VERSION_RE.match(pyproject_version):
        errors.append(f"pyproject version is not an expected release version: {pyproject_version}")
    if runtime_version != pyproject_version:
        errors.append(
            "__version__ mismatch: "
            f"src/skillreg/__init__.py has {runtime_version}, "
            f"pyproject.toml has {pyproject_version}"
        )

    if args.require_tag:
        tag = tag_from_env()
        expected = f"v{pyproject_version}"
        if tag != expected:
            errors.append(f"tag mismatch: expected {expected}, got {tag or '(none)'}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"version ok: {pyproject_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
