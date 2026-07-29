#!/usr/bin/env python3
"""Read-only checks for Git and package registry release state."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TAG_RE = re.compile(r"^v(\d+\.\d+\.\d+)$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
DEFAULT_PYPI_URL = "https://pypi.org/pypi/skillreg/json"
DEFAULT_NPM_URL = "https://registry.npmjs.org/skillreg"


class ReleaseStateError(RuntimeError):
    """Raised when Git and published package state disagree."""


def check_release_state(
    *,
    base_tag: str,
    next_version: str,
    remote: str = "origin",
    root: Path = ROOT,
    pypi_url: str | None = None,
    npm_url: str | None = None,
) -> dict[str, Any]:
    base_match = TAG_RE.fullmatch(base_tag)
    if not base_match:
        raise ReleaseStateError(f"Invalid base release tag: {base_tag}; expected vX.Y.Z")
    if not VERSION_RE.fullmatch(next_version):
        raise ReleaseStateError(f"Invalid planned version: {next_version}; expected X.Y.Z")

    remote_tags = read_remote_release_tags(remote, root)
    local_tags = set(_git(["tag", "--list"], root).splitlines())
    missing_local = sorted(tag for tag in remote_tags if tag not in local_tags)
    if missing_local:
        raise ReleaseStateError(
            "Remote release tags are missing locally; run git fetch --tags: "
            + ", ".join(missing_local)
        )
    if base_tag not in remote_tags:
        raise ReleaseStateError(f"Base tag {base_tag} does not exist on remote {remote}")

    local_base = _git(["rev-parse", f"{base_tag}^{{}}"], root)
    if remote_tags[base_tag] != local_base:
        raise ReleaseStateError(
            f"Base tag {base_tag} differs between local Git and remote {remote}"
        )

    next_tag = f"v{next_version}"
    if next_tag in remote_tags:
        raise ReleaseStateError(f"Planned tag already exists on remote {remote}: {next_tag}")

    remote_main = _git(["ls-remote", "--heads", remote, "refs/heads/main"], root)
    if not remote_main:
        raise ReleaseStateError(f"Remote {remote} has no main branch")
    remote_main_hash = remote_main.split()[0]
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", remote_main_hash, "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if ancestor.returncode != 0:
        raise ReleaseStateError(
            f"Remote {remote}/main is not an ancestor of HEAD; fetch and reconcile before release"
        )

    pypi_versions = read_registry_versions(
        pypi_url or os.environ.get("SKILLREG_PYPI_URL", DEFAULT_PYPI_URL),
        "releases",
        "PyPI",
    )
    npm_versions = read_registry_versions(
        npm_url or os.environ.get("SKILLREG_NPM_REGISTRY_URL", DEFAULT_NPM_URL),
        "versions",
        "npm",
    )
    base_version = base_match.group(1)
    registry_status = {}
    for registry, versions in (("PyPI", pypi_versions), ("npm", npm_versions)):
        if not versions:
            raise ReleaseStateError(f"{registry} has no published skillreg versions")
        highest = max(versions, key=_version_tuple)
        if next_version in versions:
            raise ReleaseStateError(
                f"{registry} already contains {next_version}, but Git tag {next_tag} is missing"
            )
        if highest != base_version:
            raise ReleaseStateError(
                f"{registry} latest published version is {highest}, "
                f"but the base Git tag is {base_tag}"
            )
        registry_status[registry.lower()] = {
            "latest": highest,
            "planned_version_exists": False,
        }

    return {
        "remote": remote,
        "base_tag": base_tag,
        "base_commit": local_base,
        "remote_main": remote_main_hash,
        "next_tag": next_tag,
        "registries": registry_status,
    }


def read_remote_release_tags(remote: str, root: Path = ROOT) -> dict[str, str]:
    output = _git(["ls-remote", "--tags", remote], root)
    direct: dict[str, str] = {}
    peeled: dict[str, str] = {}
    for line in output.splitlines():
        if not line:
            continue
        object_hash, ref = line.split(maxsplit=1)
        prefix = "refs/tags/"
        if not ref.startswith(prefix):
            continue
        name = ref.removeprefix(prefix)
        if name.endswith("^{}"):
            peeled[name.removesuffix("^{}")] = object_hash
        else:
            direct[name] = object_hash
    return {
        tag: peeled.get(tag, object_hash)
        for tag, object_hash in direct.items()
        if TAG_RE.fullmatch(tag)
    }


def read_registry_versions(url: str, versions_key: str, registry: str) -> set[str]:
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            data = json.load(response)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise ReleaseStateError(f"Unable to verify {registry} release state: {exc}") from exc
    versions = data.get(versions_key)
    if not isinstance(versions, dict):
        raise ReleaseStateError(f"Invalid {registry} registry response from {url}")
    return {version for version in versions if VERSION_RE.fullmatch(version)}


def _version_tuple(version: str) -> tuple[int, int, int]:
    return tuple(int(part) for part in version.split("."))  # type: ignore[return-value]


def _git(args: list[str], root: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown Git error"
        raise ReleaseStateError(f"Git command failed ({' '.join(args)}): {detail}")
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Check release tags and package registries.")
    parser.add_argument("--base-tag", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    try:
        state = check_release_state(
            base_tag=args.base_tag,
            next_version=args.version,
            remote=args.remote,
        )
    except ReleaseStateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.as_json:
        print(json.dumps(state, indent=2))
    else:
        print(f"Remote base tag: {state['base_tag']} ({state['base_commit'][:12]})")
        print(f"Remote main: {state['remote_main'][:12]}")
        for registry, details in state["registries"].items():
            print(f"{registry} latest: {details['latest']}")
        print(f"Planned tag is available: {state['next_tag']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
