"""Tests for builtin self-skill injection."""

from __future__ import annotations

from skillreg.services.self_skill import inject_self_skill


def test_inject_self_skill_copies_references_directory(tmp_path):
    """Builtin self-skill injection copies nested reference docs."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    target = inject_self_skill(workspace)

    assert target is not None
    assert (target / "SKILL.md").exists()
    assert (target / "references" / "install.md").exists()
    assert (target / "references" / "troubleshooting.md").exists()
