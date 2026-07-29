"""Tests for release version planning and metadata synchronization."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import versioning


def _make_version_fixture(tmp_path: Path, version: str = "1.2.0") -> Path:
    root = tmp_path
    (root / "src" / "skillreg" / "builtin" / "skillreg-skill").mkdir(parents=True)
    (root / "src" / "skillreg").mkdir(parents=True, exist_ok=True)
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
        "---\n\n"
        "# skillreg-skill\n",
        encoding="utf-8",
    )
    (root / "npm" / "package.json").write_text(
        json.dumps({"name": "skillreg", "version": version}, indent=2) + "\n",
        encoding="utf-8",
    )
    (root / "npm" / "package-lock.json").write_text(
        json.dumps(
            {
                "name": "skillreg",
                "version": version,
                "lockfileVersion": 3,
                "requires": True,
                "packages": {"": {"name": "skillreg", "version": version}},
            },
            indent=2,
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
    return root


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _make_release_repo(tmp_path: Path, version: str = "1.2.0", tag: str = "v1.2.0") -> Path:
    root = _make_version_fixture(tmp_path, version)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.name", "Test")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "chore: initial release")
    _git(root, "tag", "-a", tag, "-m", tag)
    return root


def _commit(root: Path, message: str) -> None:
    _git(root, "commit", "--allow-empty", "-qm", message)


def test_sync_version_updates_all_six_version_files(tmp_path):
    root = _make_version_fixture(tmp_path)

    versioning.sync_version("1.3.0", root)

    assert versioning.read_pyproject_version(root) == "1.3.0"
    assert versioning.read_runtime_version(root) == "1.3.0"
    assert versioning.read_builtin_skill_version(root) == "1.3.0"
    assert versioning.read_npm_package_version(root) == "1.3.0"
    assert versioning.read_npm_lock_versions(root) == ("1.3.0", "1.3.0")
    assert versioning.read_uv_lock_version(root) == "1.3.0"
    assert versioning.check_versions(root) == []


def test_check_versions_rejects_uv_lock_mismatch(tmp_path):
    root = _make_version_fixture(tmp_path)
    lock_path = root / "uv.lock"
    lock_path.write_text(
        lock_path.read_text(encoding="utf-8").replace('version = "1.2.0"', 'version = "1.1.0"'),
        encoding="utf-8",
    )

    assert any("uv lock version mismatch" in error for error in versioning.check_versions(root))


def test_check_version_cli_reports_uv_lock_mismatch(tmp_path):
    root = _make_version_fixture(tmp_path)
    (root / "scripts").mkdir()
    project_root = Path(__file__).parents[1]
    shutil.copy2(project_root / "scripts" / "versioning.py", root / "scripts" / "versioning.py")
    shutil.copy2(project_root / "scripts" / "check_version.py", root / "scripts" / "check_version.py")
    lock_path = root / "uv.lock"
    lock_path.write_text(
        lock_path.read_text(encoding="utf-8").replace('version = "1.2.0"', 'version = "1.1.0"'),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "scripts/check_version.py"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "uv lock version mismatch" in result.stderr


def test_multiple_fixes_produce_one_patch_bump(tmp_path):
    root = _make_release_repo(tmp_path)
    _commit(root, "fix: first bug")
    _commit(root, "fix(core): second bug")

    plan = versioning.plan_release(root=root)

    assert plan.bump == "patch"
    assert plan.next_version == "1.2.1"
    assert len(plan.triggers) == 2


def test_fix_and_feat_produce_one_minor_bump(tmp_path):
    root = _make_release_repo(tmp_path)
    _commit(root, "fix: a bug")
    _commit(root, "feat(cli): add release planning")

    plan = versioning.plan_release(root=root)

    assert plan.automatic_bump == "minor"
    assert plan.next_version == "1.3.0"


@pytest.mark.parametrize(
    "message",
    [
        "feat!: redesign release contract",
        "feat: redesign release contract\n\nBREAKING CHANGE: remove old bump command",
    ],
)
def test_breaking_change_wins_over_feat_and_fix(tmp_path, message):
    root = _make_release_repo(tmp_path)
    _commit(root, "fix: a bug")
    _commit(root, message)

    plan = versioning.plan_release(root=root)

    assert plan.bump == "major"
    assert plan.next_version == "2.0.0"


def test_non_release_commits_return_no_release(tmp_path):
    root = _make_release_repo(tmp_path)
    _commit(root, "docs: explain releases")
    _commit(root, "chore: update tooling")
    _commit(root, "test: cover release plan")

    plan = versioning.plan_release(root=root)

    assert plan.release_required is False
    assert plan.bump is None
    assert plan.next_version is None


def test_explicit_bump_overrides_automatic_result(tmp_path):
    root = _make_release_repo(tmp_path)
    _commit(root, "docs: explain releases")

    plan = versioning.plan_release("minor", root)

    assert plan.override is True
    assert plan.requested_bump == "minor"
    assert plan.automatic_bump is None
    assert plan.bump == "minor"
    assert plan.next_version == "1.3.0"


def test_release_and_legacy_version_sync_commits_do_not_trigger_release(tmp_path):
    root = _make_release_repo(tmp_path)
    _commit(root, "chore(release): v1.2.1")
    _commit(root, "chore: sync version 1.2.1")
    _commit(root, "chore: sync lockfile version 1.2.1")

    assert versioning.plan_release(root=root).release_required is False


def test_pending_version_is_reused_when_it_meets_minimum(tmp_path):
    root = _make_release_repo(tmp_path, "1.8.0", "v1.8.0")
    _commit(root, "feat: add dashboard release view")
    versioning.sync_version("1.9.0", root)
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "chore: sync version 1.9.0")

    plan = versioning.plan_release(root=root)

    assert plan.minimum_version == "1.9.0"
    assert plan.pending_version == "1.9.0"
    assert plan.next_version == "1.9.0"


def test_base_tag_is_selected_by_reachable_history_not_version_sort(tmp_path):
    root = _make_release_repo(tmp_path, "9.9.9", "v9.9.9")
    versioning.sync_version("1.2.0", root)
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "chore(release): v1.2.0")
    _git(root, "tag", "-a", "v1.2.0", "-m", "v1.2.0")
    _commit(root, "fix: next release")

    plan = versioning.plan_release(root=root)

    assert plan.base_tag == "v1.2.0"
    assert plan.next_version == "1.2.1"


def test_pending_version_below_required_minimum_is_rejected(tmp_path):
    root = _make_release_repo(tmp_path)
    _commit(root, "feat: add dashboard release view")
    versioning.sync_version("1.2.1", root)
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "chore: sync version 1.2.1")

    with pytest.raises(versioning.VersionPlanError, match="lower than required 1.3.0"):
        versioning.plan_release(root=root)


def test_current_version_below_base_tag_is_rejected_even_without_release_changes(tmp_path):
    root = _make_release_repo(tmp_path, "1.2.0", "v1.2.0")
    versioning.sync_version("1.1.9", root)
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "chore: stale metadata")

    with pytest.raises(versioning.VersionPlanError, match="lower than base tag v1.2.0"):
        versioning.plan_release(root=root)


def test_missing_invalid_and_unreachable_tags_have_clear_errors(tmp_path):
    missing = _make_version_fixture(tmp_path / "missing")
    _git(missing, "init", "-q", "-b", "main")
    _git(missing, "config", "user.name", "Test")
    _git(missing, "config", "user.email", "test@example.com")
    _git(missing, "add", ".")
    _git(missing, "commit", "-qm", "chore: initial")
    with pytest.raises(versioning.VersionPlanError, match="No Git tags found"):
        versioning.plan_release(root=missing)

    invalid = _make_version_fixture(tmp_path / "invalid")
    _git(invalid, "init", "-q", "-b", "main")
    _git(invalid, "config", "user.name", "Test")
    _git(invalid, "config", "user.email", "test@example.com")
    _git(invalid, "add", ".")
    _git(invalid, "commit", "-qm", "chore: initial")
    _git(invalid, "tag", "release-1.2.0")
    with pytest.raises(versioning.VersionPlanError, match="No valid SemVer tags found"):
        versioning.plan_release(root=invalid)

    unreachable = _make_release_repo(tmp_path / "unreachable")
    _git(unreachable, "checkout", "--orphan", "detached-history")
    _git(unreachable, "commit", "--allow-empty", "-qm", "fix: unrelated history")
    with pytest.raises(versioning.VersionPlanError, match="No SemVer tag is reachable"):
        versioning.plan_release(root=unreachable)


def test_tag_version_must_match_package_version_at_tag(tmp_path):
    root = _make_release_repo(tmp_path, "1.2.0", "v1.2.1")
    _commit(root, "fix: a bug")

    with pytest.raises(versioning.VersionPlanError, match="points to package version 1.2.0"):
        versioning.plan_release(root=root)


def test_prepare_updates_metadata_without_committing_or_tagging(tmp_path):
    root = _make_release_repo(tmp_path)
    _commit(root, "feat: add release planning")
    head_before = _git(root, "rev-parse", "HEAD")
    tags_before = _git(root, "tag", "--list")

    plan = versioning.prepare_release(root=root)

    assert plan.next_version == "1.3.0"
    assert versioning.check_versions(root) == []
    assert _git(root, "rev-parse", "HEAD") == head_before
    assert _git(root, "tag", "--list") == tags_before
    changed = set(_git(root, "diff", "--name-only").splitlines())
    assert changed == {
        "npm/package-lock.json",
        "npm/package.json",
        "pyproject.toml",
        "src/skillreg/__init__.py",
        "src/skillreg/builtin/skillreg-skill/SKILL.md",
        "uv.lock",
    }


def test_release_workflow_fetches_history_and_keeps_tag_version_check():
    workflow = (Path(__file__).parents[1] / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )

    assert "fetch-depth: 0" in workflow
    assert "scripts/check_version.py --require-tag" in workflow
