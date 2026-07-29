"""Integration tests for the local release command."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _write_version_files(root: Path, version: str) -> None:
    (root / "src" / "skillreg" / "builtin" / "skillreg-skill").mkdir(parents=True)
    (root / "npm").mkdir()
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "skillreg"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    (root / "src" / "skillreg" / "__init__.py").write_text(
        f'__version__ = "{version}"\n',
        encoding="utf-8",
    )
    (root / "src" / "skillreg" / "builtin" / "skillreg-skill" / "SKILL.md").write_text(
        "---\n"
        "name: skillreg-skill\n"
        "description: demo\n"
        "metadata:\n"
        f'  version: "{version}"\n'
        "---\n",
        encoding="utf-8",
    )
    (root / "npm" / "package.json").write_text(
        json.dumps({"name": "skillreg", "version": version}) + "\n",
        encoding="utf-8",
    )
    (root / "npm" / "package-lock.json").write_text(
        json.dumps(
            {
                "name": "skillreg",
                "version": version,
                "packages": {"": {"name": "skillreg", "version": version}},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "uv.lock").write_text(
        "version = 1\n"
        'requires-python = ">=3.9"\n\n'
        "[[package]]\n"
        'name = "skillreg"\n'
        f'version = "{version}"\n'
        'source = { editable = "." }\n',
        encoding="utf-8",
    )


def _make_release_checkout(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    remote = tmp_path / "origin.git"
    (root / "scripts").mkdir(parents=True)
    for name in ("release.sh", "versioning.py", "check_release_state.py"):
        shutil.copy2(ROOT / "scripts" / name, root / "scripts" / name)
    _write_version_files(root, "1.2.0")
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.name", "Test")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "chore: initial release")
    _git(root, "tag", "-a", "v1.2.0", "-m", "v1.2.0")
    _git(remote.parent, "clone", "-q", "--bare", str(root), str(remote))
    _git(root, "remote", "add", "origin", str(remote))
    _git(root, "commit", "--allow-empty", "-qm", "fix: release candidate")
    return root, remote


def _registry_file(path: Path, key: str) -> str:
    path.write_text(json.dumps({key: {"1.2.0": {}}}), encoding="utf-8")
    return path.as_uri()


def test_dry_run_leaves_worktree_head_tags_and_remote_unchanged(tmp_path):
    root, remote = _make_release_checkout(tmp_path)
    env = {
        **os.environ,
        "SKILLREG_PYPI_URL": _registry_file(tmp_path / "pypi.json", "releases"),
        "SKILLREG_NPM_REGISTRY_URL": _registry_file(tmp_path / "npm.json", "versions"),
    }
    before = {
        "status": _git(root, "status", "--porcelain=v1"),
        "head": _git(root, "rev-parse", "HEAD"),
        "tags": _git(root, "show-ref", "--tags"),
        "remote": _git(remote, "show-ref"),
    }

    result = subprocess.run(
        ["bash", "scripts/release.sh", "--dry-run"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Next version: 1.2.1" in result.stdout
    assert "Dry run complete" in result.stdout
    assert _git(root, "status", "--porcelain=v1") == before["status"]
    assert _git(root, "rev-parse", "HEAD") == before["head"]
    assert _git(root, "show-ref", "--tags") == before["tags"]
    assert _git(remote, "show-ref") == before["remote"]


def test_release_script_runs_full_gates_before_tag_and_uses_atomic_push():
    script = (ROOT / "scripts" / "release.sh").read_text(encoding="utf-8")
    prepare = script.index("scripts/versioning.py prepare")
    tag = script.index('git tag -a "$tag"')

    for command in (
        "uv run python scripts/check_version.py",
        "uv sync --extra dev",
        "uv run pytest -q",
        "uv run --with ruff ruff check src/ tests/ scripts/",
        "npm test && npm run build",
        "npm run e2e",
        "npm ci && npm test && npm pack --dry-run",
    ):
        assert prepare < script.index(command) < tag
    assert script.index("npm run build") < script.index("uv run python scripts/check_version.py")
    assert script.index("uv sync --extra dev") < script.index("uv run pytest -q")
    assert script.index("uv run python scripts/check_version.py") < script.index("npm run e2e")
    assert 'git commit --allow-empty -m "chore(release): $tag"' in script
    assert 'git push --atomic origin main "$tag"' in script
