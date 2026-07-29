"""Tests for read-only release state verification."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts import check_release_state


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _make_remote_repo(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    remote = tmp_path / "origin.git"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.name", "Test")
    _git(root, "config", "user.email", "test@example.com")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "skillreg"\nversion = "1.2.0"\n',
        encoding="utf-8",
    )
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "chore: initial")
    _git(root, "tag", "-a", "v1.2.0", "-m", "v1.2.0")
    _git(remote.parent, "clone", "-q", "--bare", str(root), str(remote))
    _git(root, "remote", "add", "origin", str(remote))
    _git(root, "commit", "--allow-empty", "-qm", "fix: next release")
    return root, remote


def _registry_file(path: Path, key: str, versions: list[str]) -> str:
    path.write_text(
        json.dumps({key: {version: {} for version in versions}}),
        encoding="utf-8",
    )
    return path.as_uri()


def test_release_state_accepts_matching_git_and_registry_state(tmp_path):
    root, _remote = _make_remote_repo(tmp_path)
    pypi = _registry_file(tmp_path / "pypi.json", "releases", ["1.2.0"])
    npm = _registry_file(tmp_path / "npm.json", "versions", ["1.2.0"])

    state = check_release_state.check_release_state(
        base_tag="v1.2.0",
        next_version="1.2.1",
        root=root,
        pypi_url=pypi,
        npm_url=npm,
    )

    assert state["registries"]["pypi"]["latest"] == "1.2.0"
    assert state["next_tag"] == "v1.2.1"


def test_release_state_rejects_registry_version_without_git_tag(tmp_path):
    root, _remote = _make_remote_repo(tmp_path)
    pypi = _registry_file(tmp_path / "pypi.json", "releases", ["1.2.0", "1.2.1"])
    npm = _registry_file(tmp_path / "npm.json", "versions", ["1.2.0"])

    with pytest.raises(check_release_state.ReleaseStateError, match="already contains 1.2.1"):
        check_release_state.check_release_state(
            base_tag="v1.2.0",
            next_version="1.2.1",
            root=root,
            pypi_url=pypi,
            npm_url=npm,
        )


def test_release_state_rejects_remote_tags_missing_locally(tmp_path):
    root, remote = _make_remote_repo(tmp_path)
    other = tmp_path / "other"
    _git(tmp_path, "clone", "-q", str(remote), str(other))
    _git(other, "config", "user.name", "Test")
    _git(other, "config", "user.email", "test@example.com")
    _git(other, "tag", "-a", "v1.2.1", "-m", "v1.2.1")
    _git(other, "push", "-q", "origin", "v1.2.1")
    pypi = _registry_file(tmp_path / "pypi.json", "releases", ["1.2.0"])
    npm = _registry_file(tmp_path / "npm.json", "versions", ["1.2.0"])

    with pytest.raises(check_release_state.ReleaseStateError, match="missing locally"):
        check_release_state.check_release_state(
            base_tag="v1.2.0",
            next_version="1.2.2",
            root=root,
            pypi_url=pypi,
            npm_url=npm,
        )
