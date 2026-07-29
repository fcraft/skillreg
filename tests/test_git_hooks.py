"""Integration tests for managed Git hook installation."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]
LEGACY_HOOK = """#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
commit_msg_file="${1:?commit message file is required}"

python3 "$repo_root/scripts/versioning.py" bump --commit-msg-file "$commit_msg_file"

git add \\
  "$repo_root/pyproject.toml" \\
  "$repo_root/src/skillreg/__init__.py" \\
  "$repo_root/src/skillreg/builtin/skillreg-skill/SKILL.md" \\
  "$repo_root/npm/package.json" \\
  "$repo_root/npm/package-lock.json"
"""


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "scripts" / "hooks").mkdir(parents=True)
    shutil.copy2(ROOT / "scripts" / "install-git-hooks.sh", root / "scripts" / "install-git-hooks.sh")
    shutil.copy2(ROOT / "scripts" / "hooks" / "commit-msg", root / "scripts" / "hooks" / "commit-msg")
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.name", "Test")
    _git(root, "config", "user.email", "test@example.com")
    (root / "tracked.txt").write_text("initial\n", encoding="utf-8")
    _git(root, "add", "tracked.txt")
    _git(root, "commit", "-qm", "chore: initial")
    return root


def _run_installer(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "scripts/install-git-hooks.sh"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_installer_installs_managed_hook_without_mutating_index(tmp_path):
    root = _make_repo(tmp_path)

    result = _run_installer(root)

    assert result.returncode == 0
    hook = root / ".git" / "hooks" / "commit-msg"
    assert hook.read_bytes() == (root / "scripts" / "hooks" / "commit-msg").read_bytes()

    (root / "tracked.txt").write_text("staged\n", encoding="utf-8")
    _git(root, "add", "tracked.txt")
    (root / "unstaged.txt").write_text("untouched\n", encoding="utf-8")
    status_before = _git(root, "status", "--porcelain=v1")
    message = root / ".git" / "COMMIT_EDITMSG"
    message.write_text("feat: ordinary feature\n", encoding="utf-8")

    subprocess.run([str(hook), str(message)], cwd=root, check=True)

    assert _git(root, "status", "--porcelain=v1") == status_before


def test_installer_replaces_exact_legacy_managed_hook(tmp_path):
    root = _make_repo(tmp_path)
    hook = root / ".git" / "hooks" / "commit-msg"
    hook.write_text(LEGACY_HOOK, encoding="utf-8")

    result = _run_installer(root)

    assert result.returncode == 0
    assert "Replacing legacy skillreg hook" in result.stdout
    assert "skillreg-managed-hook" in hook.read_text(encoding="utf-8")


def test_installer_refuses_to_overwrite_custom_hook(tmp_path):
    root = _make_repo(tmp_path)
    hook = root / ".git" / "hooks" / "commit-msg"
    custom = "#!/bin/sh\necho custom\n"
    hook.write_text(custom, encoding="utf-8")

    result = _run_installer(root)

    assert result.returncode == 1
    assert "refusing to overwrite custom hook" in result.stderr
    assert hook.read_text(encoding="utf-8") == custom
