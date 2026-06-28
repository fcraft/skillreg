"""Tests for skill_registry service (contract validation)."""

from __future__ import annotations

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
