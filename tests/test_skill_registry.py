"""Tests for skill_registry service (contract validation)."""

from __future__ import annotations

import os
import subprocess

import skillreg.services.skill_registry as registry
from skillreg.services.skill_registry import get_all, get_skill


def _make_skill_md(path, name, description="Test skill"):
    """Create a minimal SKILL.md file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n",
        encoding="utf-8",
    )


def test_get_all_contract_shape(tmp_path):
    """getAll() returns the frozen contract shape."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    _make_skill_md(skills_dir / "my-skill" / "SKILL.md", "my-skill", "A test skill")

    data = get_all(tmp_path)

    # Top-level keys
    assert set(data.keys()) == {"skills", "repoNodes", "submodules", "relationships", "generatedAt"}
    assert isinstance(data["generatedAt"], str)

    # Skills array
    assert len(data["skills"]) == 1
    s = data["skills"][0]
    assert s["id"] == "my-skill"
    assert s["name"] == "my-skill"
    assert s["description"] == "A test skill"
    assert s["type"] in ("CLI", "Reference")
    assert s["graphType"] == "isolated-skill"
    assert s["parentNode"] is None
    assert s["isSubmodule"] is False
    assert s["submodulePath"] is None
    assert s["parentSkill"] is None

    # Empty arrays for unpopulated fields (KNOWN_DEPENDENCIES always present)
    assert data["repoNodes"] == []
    assert data["submodules"] == []
    assert len(data["relationships"]) >= 0  # may include known deps


def test_get_all_graph_type_cli(tmp_path):
    """Skill under a submodule with skill/ path gets cli-skill graphType."""
    # Create a submodule dir with .git file (mock gitlink)
    repos_dir = tmp_path / "repos" / "my-cli"
    repos_dir.mkdir(parents=True)
    (repos_dir / ".git").write_text("gitdir: ../../.git/modules/repos/my-cli\n")

    # Create skill inside skill/ subdirectory
    skill_dir = repos_dir / "skill" / "my-skill"
    _make_skill_md(skill_dir / "SKILL.md", "my-skill")

    data = get_all(tmp_path)

    assert len(data["skills"]) == 1
    assert data["skills"][0]["graphType"] == "cli-skill"
    assert data["skills"][0]["isSubmodule"] is True
    assert data["skills"][0]["submodulePath"] == "repos/my-cli"


def test_get_skill_found_and_not_found(tmp_path):
    """getSkill finds by id or name, returns None for unknown."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    _make_skill_md(skills_dir / "test-skill" / "SKILL.md", "test-skill")

    found = get_skill(tmp_path, "test-skill")
    assert found is not None
    assert found["name"] == "test-skill"

    not_found = get_skill(tmp_path, "nonexistent")
    assert not_found is None


def test_get_all_empty_workspace(tmp_path):
    """Empty workspace returns valid but empty getAll result."""
    data = get_all(tmp_path)
    assert data["skills"] == []
    assert data["repoNodes"] == []
    assert data["submodules"] == []
    # KNOWN_DEPENDENCIES always present regardless of skills
    assert isinstance(data["relationships"], list)
    assert isinstance(data["generatedAt"], str)


def test_get_all_multiple_skills(tmp_path):
    """Multiple isolated skills are all discovered."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    for name in ["skill-a", "skill-b", "skill-c"]:
        _make_skill_md(skills_dir / name / "SKILL.md", name)

    data = get_all(tmp_path)
    assert len(data["skills"]) == 3
    names = {s["name"] for s in data["skills"]}
    assert names == {"skill-a", "skill-b", "skill-c"}


def test_get_all_dedupes_duplicate_skill_names_and_prefers_skills_dir(tmp_path):
    """A skill name is the dashboard/API identity, so duplicate sources collapse."""
    _make_skill_md(tmp_path / "repos" / "demo-skill" / "SKILL.md", "demo-skill", "Repo copy")
    _make_skill_md(tmp_path / "skills" / "demo-skill" / "SKILL.md", "demo-skill", "Workspace copy")

    data = get_all(tmp_path)

    matches = [s for s in data["skills"] if s["name"] == "demo-skill"]
    assert len(matches) == 1
    assert matches[0]["path"] == "skills/demo-skill"
    assert matches[0]["description"] == "Workspace copy"

    found = get_skill(tmp_path, "demo-skill")
    assert found is not None
    assert found["path"] == "skills/demo-skill"


def test_submodule_index_status_prefers_staged_gitlink(tmp_path, monkeypatch):
    """A staged parent gitlink should be treated as the current pointer."""
    submodule = tmp_path / "repos" / "demo"
    submodule.mkdir(parents=True)

    def fake_run(cmd, cwd):
        if cmd == "git ls-files -s -- repos/demo":
            return "160000 feedbeeffeedbeeffeedbeeffeedbeeffeedbeef 0\trepos/demo"
        if cmd == "git diff --cached --name-only HEAD -- repos/demo":
            return "repos/demo"
        if cmd == "git rev-parse --short HEAD":
            return "feedbee"
        raise RuntimeError(f"unexpected command: {cmd}")

    monkeypatch.setattr(registry, "_run", fake_run)

    status = registry._get_submodule_index_status(tmp_path, "repos/demo")

    assert status == {
        "indexRef": "feedbeeffeedbeeffeedbeeffeedbeeffeedbeef",
        "indexAhead": 0,
        "indexBehind": 0,
        "indexDirty": True,
    }


def test_submodule_index_status_ignores_dirty_submodule_worktree(
    tmp_path, monkeypatch,
):
    """Submodule files do not represent a parent-repo gitlink change."""
    submodule = tmp_path / "repos" / "demo"
    submodule.mkdir(parents=True)

    def fake_run(cmd, cwd):
        if cmd == "git ls-files -s -- repos/demo":
            return "160000 feedbeeffeedbeeffeedbeeffeedbeeffeedbeef 0\trepos/demo"
        if cmd == "git diff --cached --name-only HEAD -- repos/demo":
            return ""
        if cmd == "git rev-parse --short HEAD":
            return "feedbee"
        raise RuntimeError(f"unexpected command: {cmd}")

    monkeypatch.setattr(registry, "_run", fake_run)

    status = registry._get_submodule_index_status(tmp_path, "repos/demo")

    assert status["indexDirty"] is False


def test_submodule_index_status_ignores_real_dirty_submodule_worktree(tmp_path):
    """子仓库工作树改动不应伪造父仓库 gitlink 改动"""
    origin = tmp_path / "origin"
    origin.mkdir()
    workspace = tmp_path / "workspace"
    (workspace / "repos").mkdir(parents=True)
    git_env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }

    def git(cwd, *args):
        return subprocess.run(
            ["git", *args], cwd=cwd, env=git_env,
            capture_output=True, text=True, check=True,
        )

    git(origin, "init", "-q", "--initial-branch=main")
    (origin / "dist" / "generated.js").parent.mkdir(parents=True)
    (origin / "dist" / "generated.js").write_text("generated\n", encoding="utf-8")
    git(origin, "add", ".")
    git(origin, "commit", "-qm", "init")

    git(workspace, "init", "-q", "--initial-branch=main")
    git(workspace, "config", "user.email", "test@example.com")
    git(workspace, "config", "user.name", "Test")
    git(
        workspace, "-c", "protocol.file.allow=always", "submodule", "add",
        "-q", str(origin), "repos/demo",
    )
    git(workspace, "commit", "-qm", "add submodule")

    (workspace / "repos/demo/dist/generated.js").unlink()

    status = registry.get_submodule_status(workspace, "repos/demo", "main")

    assert status["dirty"] is True
    assert status["trackedDirty"] is True
    assert status["indexDirty"] is False
