"""Small, strict Git operations shared by source management."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import urllib.parse
from collections.abc import Sequence
from pathlib import Path


GIT_AUTHOR_ENV = {
    "GIT_AUTHOR_NAME": "skillreg",
    "GIT_AUTHOR_EMAIL": "skillreg@example.invalid",
    "GIT_COMMITTER_NAME": "skillreg",
    "GIT_COMMITTER_EMAIL": "skillreg@example.invalid",
}


class GitOperationError(ValueError):
    """Raised when an expected Git operation fails."""


def _redact(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https", "ssh", "git"} or not parsed.netloc:
        return value
    host = parsed.hostname or ""
    if parsed.port:
        host += f":{parsed.port}"
    return urllib.parse.urlunsplit((parsed.scheme, host, parsed.path, "", ""))


def run_git(repo: Path, args: Sequence[str], *, check: bool = True, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            capture_output=True,
            text=True,
            env={**os.environ, **GIT_AUTHOR_ENV, **(extra_env or {})},
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GitOperationError(f"git command failed: {' '.join(args)}: {exc}") from exc
    if check and result.returncode:
        detail = (result.stderr or result.stdout or "unknown git error").strip()
        safe_args = [_redact(arg) for arg in args]
        for original, safe in zip(args, safe_args):
            if original != safe:
                detail = detail.replace(original, safe)
        raise GitOperationError(f"git command failed: {' '.join(safe_args)}: {detail}")
    return result


def is_git_repo(path: Path) -> bool:
    return run_git(path, ["rev-parse", "--git-dir"], check=False).returncode == 0


def init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if not (path / ".git").exists():
        run_git(path, ["init", "-q"])


def worktree_dirty(path: Path) -> bool:
    return bool(run_git(path, ["status", "--porcelain", "--untracked-files=all"]).stdout.strip())


def commit_exact(repo: Path, paths: Sequence[str], message: str) -> str | None:
    """Commit exactly ``paths`` while preserving unrelated staged changes."""
    if not is_git_repo(repo):
        return None
    pathspecs = list(dict.fromkeys(path for path in paths if path))
    if not pathspecs:
        return None
    changed = run_git(repo, ["status", "--porcelain", "--", *pathspecs]).stdout.strip()
    if not changed:
        return None
    hook_path = Path(run_git(repo, ["rev-parse", "--git-path", "hooks/pre-commit"]).stdout.strip())
    if not hook_path.is_absolute():
        hook_path = repo / hook_path
    with tempfile.TemporaryDirectory(prefix="skillreg-git-worktree-") as worktree_name:
        index_name = str(Path(worktree_name) / ".skillreg-index")
        index_env = {"GIT_INDEX_FILE": index_name}
        head_result = run_git(repo, ["rev-parse", "HEAD"], check=False)
        head = head_result.stdout.strip() if head_result.returncode == 0 else ""
        if head:
            run_git(repo, ["read-tree", head], extra_env=index_env)
        else:
            run_git(repo, ["read-tree", "--empty"], extra_env=index_env)
        run_git(repo, ["add", "-A", "--", *pathspecs], extra_env=index_env)

        if hook_path.is_file() and os.access(hook_path, os.X_OK):
            worktree = Path(worktree_name)
            hook_index = str(worktree / ".skillreg-hook-index")
            shutil.copy2(index_name, hook_index)
            hook_env = {"GIT_INDEX_FILE": hook_index}
            run_git(repo, ["checkout-index", "-a", f"--prefix={worktree}/"], extra_env=hook_env)
            git_dir = run_git(repo, ["rev-parse", "--absolute-git-dir"]).stdout.strip()
            hook = subprocess.run(
                [str(hook_path)],
                cwd=worktree,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    **GIT_AUTHOR_ENV,
                    **hook_env,
                    "GIT_DIR": git_dir,
                    "GIT_WORK_TREE": str(worktree),
                },
                timeout=120,
            )
            if hook.returncode:
                detail = (hook.stderr or hook.stdout or "pre-commit hook failed").strip()
                raise GitOperationError(f"pre-commit hook failed: {detail}")

        tree = run_git(repo, ["write-tree"], extra_env=index_env).stdout.strip()
        args = ["commit-tree", tree, "-m", message]
        if head:
            args.extend(["-p", head])
        commit = run_git(repo, args, extra_env=index_env).stdout.strip()
        update_args = ["update-ref", "HEAD", commit]
        if head:
            update_args.append(head)
        run_git(repo, update_args)
        run_git(repo, ["reset", "-q", commit, "--", *pathspecs])
        return commit[:7]
