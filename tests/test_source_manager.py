from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from skillreg.services.npm_source import AcquiredPackage, DiscoveredSkill
from skillreg.services.source_manager import SourceManager, SourceManagerError, load_repo_manifest


PACKAGE = "@scope/design-skills"
REGISTRY = "https://registry.example/"


def make_acquired(tmp_path: Path, version: str, files: dict[str, dict[str, str]]) -> AcquiredPackage:
    temp = tmp_path / f"artifact-{version}-{len(list(tmp_path.glob('artifact-*')))}"
    root = temp / "extracted" / "package"
    root.mkdir(parents=True)
    (root / "package.json").write_text(json.dumps({"name": PACKAGE, "version": version}))
    skills = []
    for directory, content in files.items():
        skill_dir = root / directory
        skill_dir.mkdir()
        name = content["name"]
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {name} desc\n---\n\n{content.get('body', version)}\n"
        )
        if content.get("extra"):
            (skill_dir / "extra.txt").write_text(content["extra"])
        skills.append(DiscoveredSkill(name, f"{name} desc", directory, len(list(skill_dir.iterdir()))))
    return AcquiredPackage(PACKAGE, "latest", version, REGISTRY, "https://registry.example/pkg.tgz", "sha", "sha512-value", root, temp, skills)


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "workspace"
    (ws / "skills").mkdir(parents=True)
    (ws / "repos").mkdir()
    subprocess.run(["git", "init", "-q"], cwd=ws, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=ws, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=ws, check=True)
    (ws / "README.md").write_text("workspace\n")
    subprocess.run(["git", "add", "README.md"], cwd=ws, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=ws, check=True)
    return ws


def test_skill_mode_import_subset_and_frontmatter_mapping(tmp_path, workspace):
    acquired = make_acquired(tmp_path, "1.0.0", {
        "directory-one": {"name": "one"},
        "qq-genui-android-ui-code": {"name": "html-to-android"},
    })
    manager = SourceManager(workspace, acquire=lambda *args: acquired)

    preview = manager.preview_npm(PACKAGE, REGISTRY, "latest")
    result = manager.import_npm(preview["token"], mode="skill", selected_skills=["html-to-android"])

    assert (workspace / "skills/html-to-android/SKILL.md").exists()
    assert not (workspace / "skills/one").exists()
    source = manager.list_sources()[0]
    assert source["mode"] == "skill"
    assert source["skills"][0]["sourceDirectory"] == "qq-genui-android-ui-code"
    assert source["skills"][0]["targetDirectory"] == "skills/html-to-android"
    assert result["source"]["resolvedVersion"] == "1.0.0"


def test_skill_mode_conflict_force_and_local_change_guard(tmp_path, workspace):
    first = make_acquired(tmp_path, "1.0.0", {"one-dir": {"name": "one", "body": "old"}})
    second = make_acquired(tmp_path, "2.0.0", {"one-dir": {"name": "one", "body": "new", "extra": "added"}})
    queue = iter([first, second])
    manager = SourceManager(workspace, acquire=lambda *args: next(queue))
    token = manager.preview_npm(PACKAGE, REGISTRY, "latest")["token"]
    manager.import_npm(token, mode="skill", selected_skills=["one"])

    (workspace / "skills/one/SKILL.md").write_text("local edit\n")
    preview = manager.update_preview(manager.list_sources()[0]["id"])
    assert preview["status"] == "update-available"
    assert preview["localModified"] is True
    assert preview["summary"] == {"added": 1, "modified": 1, "deleted": 0, "unchanged": 0}
    with pytest.raises(SourceManagerError, match="local modifications"):
        manager.update(manager.list_sources()[0]["id"], preview["token"])

    manager.update(manager.list_sources()[0]["id"], preview["token"], force=True)
    assert "new" in (workspace / "skills/one/SKILL.md").read_text()
    assert (workspace / "skills/one/extra.txt").exists()


def test_no_change_update_and_dry_run_do_not_mutate(tmp_path, workspace):
    first = make_acquired(tmp_path, "1.0.0", {"one-dir": {"name": "one"}})
    same = make_acquired(tmp_path, "1.0.0", {"one-dir": {"name": "one"}})
    queue = iter([first, same])
    manager = SourceManager(workspace, acquire=lambda *args: next(queue))
    manager.import_npm(manager.preview_npm(PACKAGE, REGISTRY, "latest")["token"], "skill", ["one"])
    before = subprocess.run(["git", "rev-parse", "HEAD"], cwd=workspace, text=True, capture_output=True, check=True).stdout

    preview = manager.update_preview(manager.list_sources()[0]["id"])
    result = manager.update(manager.list_sources()[0]["id"], preview["token"], dry_run=True)

    assert preview["status"] == "up-to-date"
    assert preview["files"] == []
    assert result["dryRun"] is True
    assert subprocess.run(["git", "rev-parse", "HEAD"], cwd=workspace, text=True, capture_output=True, check=True).stdout == before


def test_repo_mode_initializes_independent_repo_and_preserves_unmanaged_files(tmp_path, workspace):
    first = make_acquired(tmp_path, "1.0.0", {"android-source": {"name": "html-to-android"}})
    second = make_acquired(tmp_path, "2.0.0", {"android-source": {"name": "html-to-android", "body": "updated"}})
    queue = iter([first, second])
    manager = SourceManager(workspace, acquire=lambda *args: next(queue))
    imported = manager.import_npm(
        manager.preview_npm(PACKAGE, REGISTRY, "latest")["token"],
        mode="repo",
        selected_skills=["html-to-android"],
        target_path="repos/qqgen-ui-skills",
    )
    repo = workspace / "repos/qqgen-ui-skills"
    assert (repo / ".git").exists()
    assert (repo / "skills/html-to-android/SKILL.md").exists()
    assert (repo / "source-manifest.json").exists()
    assert imported["remoteConfigured"] is False
    (repo / "AGENTS.md").write_text("keep me\n")
    subprocess.run(["git", "add", "AGENTS.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "docs: add agent notes"], cwd=repo, check=True)

    preview = manager.update_preview(imported["source"]["id"])
    manager.update(imported["source"]["id"], preview["token"])
    assert (repo / "AGENTS.md").read_text() == "keep me\n"
    committed = subprocess.run(["git", "show", "--pretty=", "--name-only", "HEAD"], cwd=repo, text=True, capture_output=True, check=True).stdout.splitlines()
    assert committed == ["skills/html-to-android/SKILL.md", "source-manifest.json"]


def test_repo_update_rejects_dirty_worktree_but_preview_allows_it(tmp_path, workspace):
    first = make_acquired(tmp_path, "1.0.0", {"one-dir": {"name": "one"}})
    second = make_acquired(tmp_path, "2.0.0", {"one-dir": {"name": "one", "body": "new"}})
    queue = iter([first, second])
    manager = SourceManager(workspace, acquire=lambda *args: next(queue))
    imported = manager.import_npm(manager.preview_npm(PACKAGE, REGISTRY, "latest")["token"], "repo", ["one"])
    repo = workspace / imported["source"]["targetPath"]
    (repo / "README.md").write_text("dirty\n")

    preview = manager.update_preview(imported["source"]["id"])
    assert preview["repoDirty"] is True
    with pytest.raises(SourceManagerError, match="working tree is not clean"):
        manager.update(imported["source"]["id"], preview["token"])


def test_load_compatible_repo_manifest(tmp_path):
    manifest = {
        "source": {"type": "npm", "package": PACKAGE, "version": "1.0.0", "registry": REGISTRY, "integrity": "sha512-value"},
        "skills": [{"source_directory": "android-source", "repository_directory": "skills/html-to-android", "name": "html-to-android"}],
    }
    (tmp_path / "source-manifest.json").write_text(json.dumps(manifest))
    converted = load_repo_manifest(tmp_path)
    assert converted["resolvedVersion"] == "1.0.0"
    assert converted["skills"][0] == {"sourceDirectory": "android-source", "targetDirectory": "skills/html-to-android", "name": "html-to-android"}


def test_repo_manifest_rejects_unsafe_source_directory(tmp_path):
    manifest = {
        "source": {"type": "npm", "package": PACKAGE, "version": "1.0.0", "registry": REGISTRY, "integrity": "sha512-value"},
        "skills": [{"source_directory": "../escape", "repository_directory": "skills/one", "name": "one"}],
    }
    (tmp_path / "source-manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(SourceManagerError, match="unsafe source directory"):
        load_repo_manifest(tmp_path)


def test_skill_import_conflict_requires_force(tmp_path, workspace):
    existing = workspace / "skills/one"
    existing.mkdir()
    (existing / "SKILL.md").write_text("existing\n")
    package = make_acquired(tmp_path, "1.0.0", {"one-dir": {"name": "one"}})
    manager = SourceManager(workspace, acquire=lambda *args: package)
    preview = manager.preview_npm(PACKAGE, REGISTRY, "latest")
    with pytest.raises(SourceManagerError, match="target already exists"):
        manager.import_npm(preview["token"], "skill", ["one"])


def test_preview_session_is_bound_to_workspace(tmp_path, workspace):
    package = make_acquired(tmp_path, "1.0.0", {"one-dir": {"name": "one"}})
    preview = SourceManager(workspace, acquire=lambda *args: package).preview_npm(PACKAGE, REGISTRY, "latest")
    other = tmp_path / "other-workspace"
    (other / "skills").mkdir(parents=True)
    (other / "repos").mkdir()
    with pytest.raises(SourceManagerError, match="another source"):
        SourceManager(other).import_npm(preview["token"], "skill", ["one"])


def test_update_rolls_back_on_store_failure(tmp_path, workspace, monkeypatch):
    first = make_acquired(tmp_path, "1.0.0", {"one-dir": {"name": "one", "body": "old"}})
    second = make_acquired(tmp_path, "2.0.0", {"one-dir": {"name": "one", "body": "new"}})
    queue = iter([first, second])
    manager = SourceManager(workspace, acquire=lambda *args: next(queue))
    imported = manager.import_npm(manager.preview_npm(PACKAGE, REGISTRY, "latest")["token"], "skill", ["one"])
    preview = manager.update_preview(imported["source"]["id"])
    monkeypatch.setattr(manager.store, "put", lambda record: (_ for _ in ()).throw(OSError("disk full")))

    with pytest.raises(OSError, match="disk full"):
        manager.update(imported["source"]["id"], preview["token"])
    assert "old" in (workspace / "skills/one/SKILL.md").read_text()


def test_new_repo_import_rolls_back_repo_and_store_on_failure(tmp_path, workspace, monkeypatch):
    package = make_acquired(tmp_path, "1.0.0", {"one-dir": {"name": "one"}})
    manager = SourceManager(workspace, acquire=lambda *args: package)
    token = manager.preview_npm(PACKAGE, REGISTRY, "latest")["token"]
    monkeypatch.setattr(manager.store, "put", lambda record: (_ for _ in ()).throw(OSError("disk full")))

    with pytest.raises(OSError, match="disk full"):
        manager.import_npm(token, "repo", ["one"], target_path="repos/rollback")

    assert not (workspace / "repos/rollback").exists()
    assert not (workspace / ".skillreg/sources.json").exists()


def test_repo_update_restores_repo_head_when_workspace_commit_fails(tmp_path, workspace, monkeypatch):
    first = make_acquired(tmp_path, "1.0.0", {"one-dir": {"name": "one", "body": "old"}})
    second = make_acquired(tmp_path, "2.0.0", {"one-dir": {"name": "one", "body": "new"}})
    queue = iter([first, second])
    manager = SourceManager(workspace, acquire=lambda *args: next(queue))
    imported = manager.import_npm(manager.preview_npm(PACKAGE, REGISTRY, "latest")["token"], "repo", ["one"])
    repo = workspace / imported["source"]["targetPath"]
    old_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, text=True, capture_output=True, check=True).stdout.strip()
    preview = manager.update_preview(imported["source"]["id"])
    import skillreg.services.source_manager as module
    real_commit = module.commit_exact
    calls = 0

    def fail_workspace_commit(path, paths, message):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("workspace commit failed")
        return real_commit(path, paths, message)

    monkeypatch.setattr(module, "commit_exact", fail_workspace_commit)
    with pytest.raises(OSError, match="workspace commit failed"):
        manager.update(imported["source"]["id"], preview["token"])

    assert subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, text=True, capture_output=True, check=True).stdout.strip() == old_head
    assert "old" in (repo / "skills/one/SKILL.md").read_text()


def test_update_diff_reports_deleted_files(tmp_path, workspace):
    first = make_acquired(tmp_path, "1.0.0", {"one-dir": {"name": "one", "body": "old", "extra": "remove"}})
    second = make_acquired(tmp_path, "2.0.0", {"one-dir": {"name": "one", "body": "new"}})
    queue = iter([first, second])
    manager = SourceManager(workspace, acquire=lambda *args: next(queue))
    imported = manager.import_npm(manager.preview_npm(PACKAGE, REGISTRY, "latest")["token"], "skill", ["one"])

    preview = manager.update_preview(imported["source"]["id"])

    assert preview["summary"]["modified"] == 1
    assert preview["summary"]["deleted"] == 1
    assert {item["status"] for item in preview["files"]} == {"modified", "deleted"}


def test_existing_repo_manifest_is_explicitly_validated_and_unmanaged_files_survive(tmp_path, workspace):
    repo = workspace / "repos/existing"
    (repo / "skills/one").mkdir(parents=True)
    (repo / "skills/one/SKILL.md").write_text("---\nname: one\n---\nold\n")
    (repo / "README.md").write_text("custom readme\n")
    (repo / "source-manifest.json").write_text(json.dumps({
        "source": {"type": "npm", "package": PACKAGE, "version": "0.9.0", "registry": REGISTRY, "integrity": "sha512-old"},
        "skills": [{"source_directory": "one-dir", "repository_directory": "skills/one", "name": "one"}],
    }))
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)
    package = make_acquired(tmp_path, "1.0.0", {"one-dir": {"name": "one", "body": "managed"}})
    manager = SourceManager(workspace, acquire=lambda *args: package)

    result = manager.import_npm(
        manager.preview_npm(PACKAGE, REGISTRY, "latest")["token"],
        "repo",
        ["one"],
        target_path="repos/existing",
    )

    assert result["source"]["resolvedVersion"] == "1.0.0"
    assert (repo / "README.md").read_text() == "custom readme\n"
    assert "managed" in (repo / "skills/one/SKILL.md").read_text()


def test_exact_commit_does_not_include_file_staged_by_hook(tmp_path, workspace):
    readme = workspace / "README.md"
    readme.write_text("staged content\n")
    subprocess.run(["git", "add", "README.md"], cwd=workspace, check=True)
    readme.write_text("unstaged content\n")
    staged_before = subprocess.run(
        ["git", "diff", "--cached", "--binary", "--", "README.md"],
        cwd=workspace,
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    unstaged_before = subprocess.run(
        ["git", "diff", "--binary", "--", "README.md"],
        cwd=workspace,
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    hooks = workspace / ".git/hooks"
    hook = hooks / "pre-commit"
    hook.write_text("#!/bin/sh\nprintf 'hook edit\\n' >> README.md\ngit add README.md\n")
    hook.chmod(0o755)
    package = make_acquired(tmp_path, "1.0.0", {"one-dir": {"name": "one"}})
    manager = SourceManager(workspace, acquire=lambda *args: package)

    manager.import_npm(manager.preview_npm(PACKAGE, REGISTRY, "latest")["token"], "skill", ["one"])

    committed = subprocess.run(["git", "show", "--pretty=", "--name-only", "HEAD"], cwd=workspace, text=True, capture_output=True, check=True).stdout.splitlines()
    assert committed == [".skillreg/sources.json", "skills/one/SKILL.md"]
    assert readme.read_text() == "unstaged content\n"
    assert subprocess.run(
        ["git", "diff", "--cached", "--binary", "--", "README.md"],
        cwd=workspace,
        text=True,
        capture_output=True,
        check=True,
    ).stdout == staged_before
    assert subprocess.run(
        ["git", "diff", "--binary", "--", "README.md"],
        cwd=workspace,
        text=True,
        capture_output=True,
        check=True,
    ).stdout == unstaged_before


def test_remote_repo_is_added_as_submodule_without_push(tmp_path, workspace, monkeypatch):
    upstream = tmp_path / "upstream"
    (upstream / "skills/one").mkdir(parents=True)
    (upstream / "skills/one/SKILL.md").write_text("---\nname: one\n---\nold\n")
    (upstream / "README.md").write_text("upstream\n")
    (upstream / "source-manifest.json").write_text(json.dumps({
        "source": {"type": "npm", "package": PACKAGE, "version": "0.9.0", "registry": REGISTRY, "integrity": "sha512-old"},
        "skills": [{"source_directory": "one-dir", "repository_directory": "skills/one", "name": "one"}],
    }))
    subprocess.run(["git", "init", "-q"], cwd=upstream, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=upstream, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=upstream, check=True)
    subprocess.run(["git", "add", "."], cwd=upstream, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=upstream, check=True)
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "clone", "-q", "--bare", str(upstream), str(remote)], check=True)
    remote_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=remote, text=True, capture_output=True, check=True).stdout.strip()
    monkeypatch.setenv("GIT_ALLOW_PROTOCOL", "file")
    package = make_acquired(tmp_path, "1.0.0", {"one-dir": {"name": "one", "body": "managed"}})
    manager = SourceManager(workspace, acquire=lambda *args: package)

    result = manager.import_npm(
        manager.preview_npm(PACKAGE, REGISTRY, "latest")["token"],
        "repo",
        ["one"],
        target_path="repos/remote-skills",
        remote=str(remote),
    )

    assert result["remoteConfigured"] is True
    assert (workspace / ".gitmodules").exists()
    assert (workspace / "repos/remote-skills/.git").is_file()
    assert subprocess.run(["git", "rev-parse", "HEAD"], cwd=remote, text=True, capture_output=True, check=True).stdout.strip() == remote_head
    committed = subprocess.run(["git", "show", "--pretty=", "--name-only", "HEAD"], cwd=workspace, text=True, capture_output=True, check=True).stdout.splitlines()
    assert committed == [".gitmodules", ".skillreg/sources.json", "repos/remote-skills"]


def test_existing_submodule_takeover_commits_updated_gitlink_only(tmp_path, workspace, monkeypatch):
    upstream = tmp_path / "existing-upstream"
    (upstream / "skills/one").mkdir(parents=True)
    (upstream / "skills/one/SKILL.md").write_text("---\nname: one\n---\nold\n")
    (upstream / "README.md").write_text("upstream\n")
    (upstream / "source-manifest.json").write_text(json.dumps({
        "source": {"type": "npm", "package": PACKAGE, "version": "0.9.0", "registry": REGISTRY, "integrity": "sha512-old"},
        "skills": [{"source_directory": "one-dir", "repository_directory": "skills/one", "name": "one"}],
    }))
    subprocess.run(["git", "init", "-q"], cwd=upstream, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=upstream, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=upstream, check=True)
    subprocess.run(["git", "add", "."], cwd=upstream, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=upstream, check=True)
    remote = tmp_path / "existing-remote.git"
    subprocess.run(["git", "clone", "-q", "--bare", str(upstream), str(remote)], check=True)
    monkeypatch.setenv("GIT_ALLOW_PROTOCOL", "file")
    subprocess.run(["git", "submodule", "add", "-q", str(remote), "repos/existing-skills"], cwd=workspace, check=True)
    subprocess.run(["git", "add", ".gitmodules", "repos/existing-skills"], cwd=workspace, check=True)
    subprocess.run(["git", "commit", "-qm", "add existing submodule"], cwd=workspace, check=True)
    readme = workspace / "README.md"
    readme.write_text("workspace\nkeep staged\n")
    subprocess.run(["git", "add", "README.md"], cwd=workspace, check=True)
    package = make_acquired(tmp_path, "1.0.0", {"one-dir": {"name": "one", "body": "managed"}})
    manager = SourceManager(workspace, acquire=lambda *args: package)

    result = manager.import_npm(
        manager.preview_npm(PACKAGE, REGISTRY, "latest")["token"],
        "repo",
        ["one"],
        target_path="repos/existing-skills",
    )

    assert result["source"]["resolvedVersion"] == "1.0.0"
    committed = subprocess.run(["git", "show", "--pretty=", "--name-only", "HEAD"], cwd=workspace, text=True, capture_output=True, check=True).stdout.splitlines()
    assert committed == [".skillreg/sources.json", "repos/existing-skills"]
    staged = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=workspace, text=True, capture_output=True, check=True).stdout.splitlines()
    assert staged == ["README.md"]
    assert subprocess.run(["git", "status", "--porcelain", "--", "repos/existing-skills"], cwd=workspace, text=True, capture_output=True, check=True).stdout == ""
