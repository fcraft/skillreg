from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from skillreg.services.git_ops import GitIdentityRequiredError, commit_exact


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_commit_exact_uses_configured_repository_identity(tmp_path: Path) -> None:
    repo = tmp_path / "workspace"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Workspace User")
    _git(repo, "config", "user.email", "workspace@example.com")
    (repo / "README.md").write_text("workspace\n")

    commit_exact(repo, ["README.md"], "chore: initialize workspace")

    assert _git(repo, "show", "-s", "--format=%an <%ae>|%cn <%ce>", "HEAD") == (
        "Workspace User <workspace@example.com>|"
        "Workspace User <workspace@example.com>"
    )


def test_commit_exact_requires_identity_when_git_has_none(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", os.devnull)
    for name in (
        "GIT_AUTHOR_NAME",
        "GIT_AUTHOR_EMAIL",
        "GIT_COMMITTER_NAME",
        "GIT_COMMITTER_EMAIL",
    ):
        monkeypatch.delenv(name, raising=False)
    repo = tmp_path / "workspace"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "README.md").write_text("workspace\n")

    with pytest.raises(GitIdentityRequiredError) as caught:
        commit_exact(repo, ["README.md"], "chore: initialize workspace")

    assert caught.value.repo == repo
    assert _git(repo, "status", "--short") == "?? README.md"
