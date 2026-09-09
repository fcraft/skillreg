"""Saved-target inventory is bounded, source-independent and read-only"""

import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from skillreg import config
from skillreg.cli import cli
from skillreg.services import sync_files, sync_inventory, sync_targets


@pytest.fixture
def target(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path)
    return sync_targets.add_target("inventory", str(tmp_path / "installed"))


def make_skill(target, name, content="# Remote only\n"):
    directory = Path(target["path"]) / name
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text(content)
    return directory


def test_inventory_does_not_create_missing_target(target):
    result = sync_inventory.inspect_target(target["id"])
    assert result["exists"] is False
    assert result["skills"] == []
    assert result["targetId"] == target["id"]
    assert result["observedAt"]
    assert not Path(target["path"]).exists()


def test_inventory_lists_remote_only_without_reading_trees(target, monkeypatch):
    remote = make_skill(target, "remote-only")
    (remote / "nested").mkdir()
    os.mkfifo(remote / "nested" / "never-read")
    make_skill(target, "alpha")
    make_skill(target, ".hidden")
    (Path(target["path"]) / "not-a-skill").mkdir()
    monkeypatch.setattr(
        sync_files, "tree_snapshot", lambda *args: pytest.fail("No recursive snapshot")
    )
    monkeypatch.setattr(
        Path, "read_bytes", lambda *args: pytest.fail("No document reads")
    )
    before = (remote / "SKILL.md").stat()
    result = sync_inventory.inspect_target(target["id"])
    assert [skill["name"] for skill in result["skills"]] == ["alpha", "remote-only"]
    assert all("status" not in skill for skill in result["skills"])
    assert (remote / "SKILL.md").stat().st_mtime_ns == before.st_mtime_ns
    assert (
        sync_inventory.read_skill(target["id"], "remote-only")["content"]
        == "# Remote only\n"
    )


def test_inventory_skips_links_and_nonregular_documents(target, tmp_path):
    external = tmp_path / "external"
    external.mkdir()
    (external / "SKILL.md").write_text("outside")
    directory = make_skill(target, "linked-document")
    (directory / "SKILL.md").unlink()
    (directory / "SKILL.md").symlink_to(external / "SKILL.md")
    (Path(target["path"]) / "linked-directory").symlink_to(external)
    fifo = Path(target["path"]) / "fifo"
    fifo.mkdir()
    os.mkfifo(fifo / "SKILL.md")
    result = sync_inventory.inspect_target(target["id"])
    assert result["skills"] == []
    assert {item["name"] for item in result["skipped"]} == {
        "linked-directory",
        "linked-document",
        "fifo",
    }
    for name in [
        "linked-directory",
        "linked-document",
        "fifo",
        "../external",
        "/external",
    ]:
        with pytest.raises((sync_files.SyncError, OSError)):
            sync_inventory.read_skill(target["id"], name)


def test_inventory_and_document_limits(target, monkeypatch):
    make_skill(target, "alpha", "a" * (sync_files.MAX_DOCUMENT + 5))
    make_skill(target, "beta")
    monkeypatch.setattr(sync_files, "MAX_INVENTORY", 1)
    result = sync_inventory.inspect_target(target["id"])
    assert result["truncated"]
    assert len(result["skills"]) == 1
    document = sync_inventory.read_skill(target["id"], "alpha")
    assert document["truncated"]
    assert len(document["content"]) == sync_files.MAX_DOCUMENT


def test_inventory_cli_and_api_resolve_only_saved_targets(target):
    make_skill(target, "remote-only")
    runner = CliRunner()
    for command in [
        ["target", "inventory", target["id"]],
        ["target", "read-skill", target["id"], "remote-only"],
    ]:
        result = runner.invoke(cli, command)
        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["targetId"] == target["id"]
        assert runner.invoke(cli, command[:2] + ["-h"]).exit_code == 0
    from skillreg.server import create_app

    client = TestClient(create_app())
    prefix = "/api/targets/" + target["id"]
    assert (
        client.get(prefix + "/inventory").json()["skills"][0]["name"] == "remote-only"
    )
    assert (
        client.get(prefix + "/skills/remote-only/document").json()["content"]
        == "# Remote only\n"
    )
    assert client.get("/api/targets/unknown/inventory").status_code == 404
    assert client.get(prefix + "/skills/missing/document").status_code == 400
