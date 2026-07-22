"""Tests for import service and workspace creation."""

from __future__ import annotations

import tempfile
import subprocess
import zipfile
from pathlib import Path

import pytest
import skillreg.config as cfgmod
from skillreg.services import importer


def _configure_workspace(ws_path, monkeypatch, cfg_path=None):
    """Configure workspace path in config."""
    if cfg_path is None:
        cfg_path = ws_path.parent / "config.json"
    monkeypatch.setattr(cfgmod, "CONFIG_FILE", cfg_path)
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", cfg_path.parent)
    # Pre-set workspace_path in config
    cfg = cfgmod.load_config(cfg_path)
    cfg.workspace_path = str(ws_path)
    cfgmod.save_config(cfg, cfg_path)


class TestWorkspaceCreation:
    def test_creates_workspace(self, tmp_path, monkeypatch):
        ws = tmp_path / "my-workspace"
        _configure_workspace(ws, monkeypatch)

        result = importer.create_workspace(str(ws))

        assert result["workspace_path"] == str(ws)
        assert result["has_git"] is True
        assert result["has_skills_dir"] is True
        assert result["has_repos_dir"] is True
        assert result["initial_commit"]
        assert result["remote_configured"] is False
        assert (ws / ".git").exists()
        assert (ws / "skills").is_dir()
        assert (ws / "repos").is_dir()
        assert (ws / "skills" / ".gitkeep").exists()
        assert (ws / "repos" / ".gitkeep").exists()
        assert (ws / ".gitignore").exists()
        assert ".skillreg/builtin/" in (ws / ".gitignore").read_text()
        committed_paths = subprocess.run(
            ["git", "show", "--pretty=", "--name-only", "HEAD"],
            cwd=ws,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        assert committed_paths == [
            ".gitignore",
            "README.md",
            "repos/.gitkeep",
            "skills/.gitkeep",
        ]

    def test_rejects_nonempty_dir(self, tmp_path, monkeypatch):
        ws = tmp_path / "nonempty"
        ws.mkdir()
        (ws / "existing.txt").write_text("hi")
        _configure_workspace(ws, monkeypatch)

        with pytest.raises(ValueError, match="not empty"):
            importer.create_workspace(str(ws))


class TestImportValidation:
    def test_validates_valid_skill(self, tmp_path, monkeypatch):
        ws = tmp_path / "workspace"
        importer.create_workspace(str(ws))

        src = tmp_path / "source"
        src.mkdir()
        (src / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A test\n---\n\n# test-skill\n",
            encoding="utf-8",
        )

        _configure_workspace(ws, monkeypatch)
        result = importer.validate_import_source(str(src))
        assert result["valid"] is True
        assert result["skillName"] == "test-skill"
        assert result["conflict"]["exists"] is False

    def test_rejects_missing_skill_md(self, tmp_path, monkeypatch):
        ws = tmp_path / "workspace"
        importer.create_workspace(str(ws))

        src = tmp_path / "source"
        src.mkdir()
        (src / "README.md").write_text("# Not a skill")

        _configure_workspace(ws, monkeypatch)
        result = importer.validate_import_source(str(src))
        assert result["valid"] is False
        assert "SKILL.md" in result.get("error", "")

    def test_rejects_invalid_name(self, tmp_path, monkeypatch):
        ws = tmp_path / "workspace"
        importer.create_workspace(str(ws))

        src = tmp_path / "source"
        src.mkdir()
        (src / "SKILL.md").write_text(
            "---\nname: Invalid Name!\n---\n\n# bad\n",
            encoding="utf-8",
        )

        _configure_workspace(ws, monkeypatch)
        result = importer.validate_import_source(str(src))
        assert result["valid"] is False


class TestSkillImport:
    def test_register_commits_only_new_skill_and_preserves_existing_changes(self, tmp_path, monkeypatch):
        ws = tmp_path / "workspace"
        importer.create_workspace(str(ws))

        readme = ws / "README.md"
        staged_content = readme.read_text(encoding="utf-8") + "\nstaged change\n"
        readme.write_text(staged_content, encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=ws, check=True)
        working_content = staged_content + "unstaged change\n"
        readme.write_text(working_content, encoding="utf-8")
        (ws / "scratch.txt").write_text("untracked\n", encoding="utf-8")

        src = tmp_path / "source"
        src.mkdir()
        (src / "SKILL.md").write_text(
            "---\nname: isolated-skill\n---\n\n# Isolated\n",
            encoding="utf-8",
        )

        _configure_workspace(ws, monkeypatch)
        importer.import_skill(str(src))

        committed_paths = subprocess.run(
            ["git", "show", "--pretty=", "--name-only", "HEAD"],
            cwd=ws,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        assert committed_paths == ["skills/isolated-skill/SKILL.md"]
        assert subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=ws,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines() == ["README.md"]
        assert subprocess.run(
            ["git", "diff", "--name-only"],
            cwd=ws,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines() == ["README.md"]
        assert subprocess.run(
            ["git", "show", ":README.md"],
            cwd=ws,
            capture_output=True,
            text=True,
            check=True,
        ).stdout == staged_content
        assert readme.read_text(encoding="utf-8") == working_content
        assert (ws / "scratch.txt").read_text(encoding="utf-8") == "untracked\n"

    def test_imports_skill_to_workspace(self, tmp_path, monkeypatch):
        ws = tmp_path / "workspace"
        importer.create_workspace(str(ws))

        src = tmp_path / "source"
        src.mkdir()
        (src / "SKILL.md").write_text(
            "---\nname: my-imported-skill\n---\n\n# Hello\n",
            encoding="utf-8",
        )
        (src / "tool.py").write_text("print('hello')")

        _configure_workspace(ws, monkeypatch)
        result = importer.import_skill(str(src))

        assert result["name"] == "my-imported-skill"
        assert result["skillPath"] == "skills/my-imported-skill"
        assert result["filesCopied"] >= 2
        assert (ws / "skills" / "my-imported-skill" / "SKILL.md").exists()
        assert (ws / "skills" / "my-imported-skill" / "tool.py").exists()

    def test_import_duplicate_without_force(self, tmp_path, monkeypatch):
        ws = tmp_path / "workspace"
        importer.create_workspace(str(ws))

        src = tmp_path / "source"
        src.mkdir()
        (src / "SKILL.md").write_text(
            "---\nname: dup-skill\n---\n\n# dup\n",
            encoding="utf-8",
        )

        _configure_workspace(ws, monkeypatch)
        importer.import_skill(str(src))

        with pytest.raises(ValueError, match="already exists"):
            importer.import_skill(str(src))

    def test_import_duplicate_with_force(self, tmp_path, monkeypatch):
        ws = tmp_path / "workspace"
        importer.create_workspace(str(ws))

        src1 = tmp_path / "source1"
        src1.mkdir()
        (src1 / "SKILL.md").write_text(
            "---\nname: force-skill\n---\n\n# v1\n",
            encoding="utf-8",
        )

        src2 = tmp_path / "source2"
        src2.mkdir()
        (src2 / "SKILL.md").write_text(
            "---\nname: force-skill\n---\n\n# v2\n",
            encoding="utf-8",
        )

        _configure_workspace(ws, monkeypatch)
        importer.import_skill(str(src1))
        result = importer.import_skill(str(src2), force=True)

        assert result["name"] == "force-skill"
        content = (ws / "skills" / "force-skill" / "SKILL.md").read_text()
        assert "v2" in content


class TestZipImport:
    def test_extracts_zip(self, tmp_path):
        src = tmp_path / "zipped-skill"
        src.mkdir()
        (src / "SKILL.md").write_text(
            "---\nname: zipped\n---\n\n# zipped\n",
            encoding="utf-8",
        )

        zip_path = tmp_path / "skill.zip"
        with zipfile.ZipFile(str(zip_path), "w") as zf:
            for f in src.rglob("*"):
                if f.is_file():
                    zf.write(str(f), str(f.relative_to(src)))

        buf = zip_path.read_bytes()
        result = importer.extract_zip(buf)
        assert result["tempPath"]
        assert Path(result["extractedRoot"]).exists()


class TestDirectoryUpload:
    def test_stores_selected_folder(self):
        result = importer.store_directory_upload([
            ("chosen-skill/SKILL.md", b"---\nname: chosen-skill\n---\n"),
            ("chosen-skill/scripts/run.py", b"print('ok')\n"),
        ])

        try:
            root = Path(result["extractedRoot"])
            assert root.name == "chosen-skill"
            assert (root / "SKILL.md").read_bytes().startswith(b"---")
            assert (root / "scripts" / "run.py").exists()
        finally:
            importer.cleanup_temp(result["tempPath"])

    @pytest.mark.parametrize("path", [
        "../SKILL.md",
        "/tmp/SKILL.md",
        "C:/temp/SKILL.md",
        "skill/../../SKILL.md",
    ])
    def test_rejects_unsafe_paths(self, path):
        with pytest.raises(ValueError, match="Invalid directory upload path"):
            importer.store_directory_upload([(path, b"content")])

    def test_wraps_files_without_browser_relative_paths(self):
        result = importer.store_directory_upload([
            ("SKILL.md", b"---\nname: selected\n---\n"),
            ("tool.py", b"print('ok')\n"),
        ])

        try:
            root = Path(result["extractedRoot"])
            assert root.name == "selected-folder"
            assert (root / "SKILL.md").exists()
            assert (root / "tool.py").exists()
        finally:
            importer.cleanup_temp(result["tempPath"])


class TestCleanup:
    def test_cleanup_temp(self):
        tp = Path(tempfile.gettempdir()) / "skillreg-test-cleanup"
        tp.mkdir(parents=True, exist_ok=True)
        (tp / "dummy.txt").write_text("temp")

        importer.cleanup_temp(str(tp))
        assert not tp.exists()

    def test_cleanup_rejects_non_tmpdir(self, tmp_path):
        # Use a path clearly outside the temp directory
        outside = Path.cwd() / "skillreg-test-outside"
        with pytest.raises(ValueError, match="not in tmpdir"):
            importer.cleanup_temp(str(outside))
