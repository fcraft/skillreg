"""Tests for release version metadata helpers."""

from __future__ import annotations

from pathlib import Path

from scripts import versioning


def _make_version_fixture(tmp_path: Path, version: str = "0.1.1") -> Path:
    root = tmp_path
    (root / "src" / "skillreg" / "builtin" / "skillreg-skill").mkdir(parents=True)
    (root / "src" / "skillreg").mkdir(parents=True, exist_ok=True)
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
    return root


def test_check_versions_includes_builtin_skill(tmp_path):
    root = _make_version_fixture(tmp_path)

    assert versioning.check_versions(root) == []

    skill_path = root / "src" / "skillreg" / "builtin" / "skillreg-skill" / "SKILL.md"
    skill_path.write_text(
        skill_path.read_text(encoding="utf-8").replace('version: "0.1.1"', 'version: "0.1.0"'),
        encoding="utf-8",
    )

    errors = versioning.check_versions(root)
    assert any("builtin skill version mismatch" in error for error in errors)


def test_sync_version_updates_all_version_files(tmp_path):
    root = _make_version_fixture(tmp_path)

    versioning.sync_version("1.2.0", root)

    assert versioning.read_pyproject_version(root) == "1.2.0"
    assert versioning.read_runtime_version(root) == "1.2.0"
    assert versioning.read_builtin_skill_version(root) == "1.2.0"


def test_bump_rules_force_major_one():
    assert versioning.bump_version_for_message("0.1.1", "feat: add cli") == "1.2.0"
    assert versioning.bump_version_for_message("1.2.0", "fix: bug") == "1.2.1"
    assert versioning.bump_version_for_message("2.9.9", "docs: update") == "1.9.10"


def test_bump_from_commit_message_updates_files(tmp_path):
    root = _make_version_fixture(tmp_path)
    msg = tmp_path / "COMMIT_EDITMSG"
    msg.write_text("feat: expand cli\n\nbody\n", encoding="utf-8")

    next_version = versioning.bump_from_commit_message(msg, root)

    assert next_version == "1.2.0"
    assert versioning.check_versions(root) == []
