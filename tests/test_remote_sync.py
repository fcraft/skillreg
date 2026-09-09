"""Remote sync contracts, using the same worker locally for filesystem assertions"""

from __future__ import annotations

import ast
import base64
import hashlib
import io
import json
import os
import shlex
import subprocess
import tarfile
from pathlib import Path

import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from skillreg import config
from skillreg.cli import cli
from skillreg.services import (
    ssh_connections,
    sync_files,
    sync_runs,
    sync_targets,
    sync_manager,
)
from skillreg.services.sync_files import SyncError


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "config" / "config.json")
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path / "config")
    monkeypatch.setattr(sync_manager, "_PROJECTS_DIR", tmp_path / "config")
    monkeypatch.setattr(
        sync_manager, "_PROJECTS_FILE", tmp_path / "config" / "projects.json"
    )
    root = tmp_path / "workspace"
    source = root / "skills" / "demo"
    source.mkdir(parents=True)
    (source / "SKILL.md").write_text(
        "---\nname: demo\ndescription: Demo\n---\n\n# Demo\n"
    )
    (source / "run.sh").write_text("#!/bin/sh\nexit 0\n")
    (source / "run.sh").chmod(0o755)
    cfg = config.load_config()
    cfg.workspace_path = str(root)
    config.save_config(cfg)
    target = sync_targets.add_target("test", str(tmp_path / "installed"))
    return root, source, target


def test_preview_install_and_idempotent_history(env):
    root, source, target = env
    planned = sync_runs.preview([target["id"]], ["demo"])
    assert planned["targets"][0]["skills"][0]["status"] == "missing"
    assert not Path(target["path"]).exists()
    assert "bundle" not in json.dumps(planned)
    run = sync_runs.create_run(planned["id"], background=False)
    assert run["state"] == "succeeded"
    assert run["results"][0]["skills"][0]["changed"]
    installed = Path(target["path"]) / "demo"
    assert (installed / "SKILL.md").read_bytes() == (source / "SKILL.md").read_bytes()
    assert os.access(installed / "run.sh", os.X_OK)
    assert sync_runs.get_run(run["id"])["workspace"] == str(root)
    second = sync_runs.create_run(
        sync_runs.preview([target["id"]], ["demo"])["id"], background=False
    )
    assert second["state"] == "succeeded"
    assert second["results"][0]["skills"][0]["changed"] is False
    assert len(sync_runs.history()) == 2
    assert sync_runs.observations()[0]["skills"][0]["status"] == "synced"


def test_modified_requires_confirmation_and_cas_even_with_force(env):
    _, source, target = env
    sync_runs.create_run(
        sync_runs.preview([target["id"]], ["demo"])["id"], background=False
    )
    installed = Path(target["path"]) / "demo"
    (installed / "run.sh").write_text("local change\n")
    plan = sync_runs.preview([target["id"]], ["demo"])
    assert plan["requiresOverwrite"]
    with pytest.raises(SyncError, match="confirm overwrite"):
        sync_runs.create_run(plan["id"], background=False)
    (installed / "run.sh").write_text("new change after confirmation\n")
    run = sync_runs.create_run(plan["id"], force=True, background=False)
    assert run["state"] == "failed"
    assert run["results"][0]["skills"][0]["error"]["code"] == "target-changed"
    assert (installed / "run.sh").read_text() == "new change after confirmation\n"
    retry = sync_runs.retry_preview(run["id"])
    result = sync_runs.create_run(retry["id"], force=True, background=False)
    assert result["state"] == "succeeded"
    assert (installed / "run.sh").read_bytes() == (source / "run.sh").read_bytes()


def test_source_change_and_workspace_switch_invalidate_preview(env, tmp_path):
    _, source, target = env
    plan = sync_runs.preview([target["id"]], ["demo"])
    (source / "run.sh").write_text("changed source\n")
    with pytest.raises(SyncError, match="Source changed"):
        sync_runs.create_run(plan["id"], background=False)
    plan = sync_runs.preview([target["id"]], ["demo"])
    other = tmp_path / "other"
    (other / "skills").mkdir(parents=True)
    cfg = config.load_config()
    cfg.workspace_path = str(other)
    config.save_config(cfg)
    with pytest.raises(SyncError, match="Workspace changed"):
        sync_runs.create_run(plan["id"], background=False)


def test_partial_failure_and_preview_consumed_once(env, tmp_path, monkeypatch):
    _, _, first = env
    second = sync_targets.add_target("second", str(tmp_path / "second"))
    planned = sync_runs.preview([first["id"], second["id"]], ["demo"])
    original = ssh_connections.call

    def fail_one(connection, request, **kwargs):
        if request["operation"] == "install" and request["path"] == second["path"]:
            raise SyncError("connection lost", "offline", True)
        return original(connection, request, **kwargs)

    monkeypatch.setattr(ssh_connections, "call", fail_one)
    run = sync_runs.create_run(planned["id"], background=False)
    assert run["state"] == "partially-succeeded"
    assert [r["state"] for r in run["results"]] == ["succeeded", "failed"]
    with pytest.raises(SyncError, match="already used"):
        sync_runs.create_run(planned["id"], background=False)
    retry = sync_runs.retry_preview(run["id"])
    assert [t["target"]["id"] for t in retry["targets"]] == [second["id"]]


def test_atomic_exchange_failure_preserves_existing_skill(env, monkeypatch):
    _, source, target = env
    sync_runs.create_run(
        sync_runs.preview([target["id"]], ["demo"])["id"], background=False
    )
    before = sync_files.tree_snapshot(Path(target["path"]) / "demo")
    (source / "run.sh").write_text("new version\n")

    def fail(*args):
        raise OSError("simulated exchange failure")

    monkeypatch.setattr(sync_files, "exchange_directories", fail)
    run = sync_runs.create_run(
        sync_runs.preview([target["id"]], ["demo"])["id"], force=True, background=False
    )
    assert run["state"] == "failed"
    assert sync_files.tree_snapshot(Path(target["path"]) / "demo") == before
    assert list(Path(target["path"]).glob(".skillreg-stage-*")) == []


@pytest.mark.parametrize(
    "member_name", ["../escape", "/absolute", "C:/drive", "nested/../../escape"]
)
def test_archive_rejects_unsafe_members(tmp_path, member_name):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        member = tarfile.TarInfo(member_name)
        member.size = 1
        archive.addfile(member, io.BytesIO(b"x"))
    raw = buffer.getvalue()
    with pytest.raises(SyncError):
        sync_files.unpack_bundle(
            base64.b64encode(raw).decode(), hashlib.sha256(raw).hexdigest(), tmp_path
        )


def test_source_and_target_symlinks_are_rejected(env, tmp_path):
    _, source, target = env
    (source / "link").symlink_to(tmp_path)
    with pytest.raises(SyncError, match="regular skill"):
        sync_runs.preview([target["id"]], ["demo"])
    (source / "link").unlink()
    Path(target["path"]).symlink_to(tmp_path)
    preview = sync_runs.preview([target["id"]], ["demo"])
    assert preview["targets"][0]["error"]["code"] == "unsafe-path"


def test_legacy_target_identity_and_group_survive_label_change(env, tmp_path):
    _, _, target = env
    group = sync_manager.create_project("demo-group", [target["path"]])
    sync_targets.update_target(target["id"], name="new name")
    assert sync_manager.get_project(group["id"])["targetIds"] == [target["id"]]
    cfg = config.load_config()
    cfg.targets = [str(tmp_path / "legacy")]
    config.save_config(cfg)
    old = sync_targets.target_records()[0]
    sync_targets.update_target(old["id"], name="persisted label")
    assert sync_targets.target_records()[0]["id"] == old["id"]
    assert sync_targets.resolve_target(old["id"])["name"] == "persisted label"


def test_connection_arguments_and_python36_worker(env):
    connection = ssh_connections.save_connection("dev", "dev1", "user", 2222)
    args = ssh_connections.ssh_arguments(connection)
    assert "StrictHostKeyChecking=yes" in args
    assert "BatchMode=yes" in args
    assert args[-1] == "dev1"
    with pytest.raises(SyncError):
        ssh_connections.save_connection("bad", "-oProxyCommand=whoami")
    with pytest.raises(SyncError):
        ssh_connections.save_connection("bad", "host; echo bad")
    ast.parse(Path(sync_files.__file__).read_text(), feature_version=(3, 6))


def test_cli_and_api_sync_run_roundtrip(env):
    _, _, target = env
    runner = CliRunner()
    for command in [
        ["connection", "-h"],
        ["sync", "preview", "-h"],
        ["target", "discover", "-h"],
    ]:
        assert runner.invoke(cli, command).exit_code == 0
    result = runner.invoke(
        cli, ["sync", "execute", "--target-id", target["id"], "--skill", "demo"]
    )
    assert result.exit_code == 0, result.output
    run = json.loads(result.output)
    assert run["state"] == "succeeded"
    from skillreg.server import create_app

    client = TestClient(create_app())
    assert client.get("/api/sync/runs/" + run["id"]).json()["state"] == "succeeded"
    response = client.post(
        "/api/sync/preview", json={"targetIds": [target["id"]], "skills": ["demo"]}
    )
    assert response.status_code == 200
    assert response.json()["targets"][0]["skills"][0]["status"] == "synced"
    invalid = client.post("/api/sync/runs", json={"previewId": "missing"})
    assert invalid.status_code == 409


def test_cancel_during_install_stops_the_next_skill(env, monkeypatch):
    root, _, target = env
    second = root / "skills" / "second"
    second.mkdir()
    (second / "SKILL.md").write_text("---\nname: second\ndescription: Second\n---\n")
    original = ssh_connections.call

    def cancel_during_install(connection, request, **kwargs):
        if request["operation"] == "install":
            sync_runs.cancel_run(request["runId"])
        return original(connection, request, **kwargs)

    monkeypatch.setattr(ssh_connections, "call", cancel_during_install)
    planned = sync_runs.preview([target["id"]], ["demo", "second"])
    run = sync_runs.create_run(planned["id"], background=False)
    assert [s["state"] for s in run["results"][0]["skills"]] == [
        "succeeded",
        "cancelled",
    ]
    assert not (Path(target["path"]) / "second").exists()
    assert run["cancelRequested"] is True


def test_retry_preserves_each_targets_skill_selection(env, tmp_path, monkeypatch):
    root, _, first = env
    second_source = root / "skills" / "second"
    second_source.mkdir()
    (second_source / "SKILL.md").write_text(
        "---\nname: second\ndescription: Second\n---\n"
    )
    sync_targets.update_target(first["id"], skills=["demo"])
    second = sync_targets.add_target(
        "second", str(tmp_path / "second-target"), skills=["second"]
    )
    original = ssh_connections.call

    def unavailable(connection, request, **kwargs):
        if request["path"] == second["path"]:
            raise SyncError("offline", "offline", True)
        return original(connection, request, **kwargs)

    monkeypatch.setattr(ssh_connections, "call", unavailable)
    plan = sync_runs.preview([first["id"], second["id"]])
    run = sync_runs.create_run(plan["id"], background=False)
    assert run["state"] == "partially-succeeded"
    monkeypatch.setattr(ssh_connections, "call", original)
    sync_targets.update_target(second["id"], skills=["demo"])
    retry = sync_runs.retry_preview(run["id"])
    assert [s["name"] for s in retry["targets"][0]["skills"]] == ["second"]


@pytest.mark.skipif(
    not os.environ.get("SKILLREG_TEST_SSH_HOST"),
    reason="Set SKILLREG_TEST_SSH_HOST for opt-in real SSH acceptance",
)
def test_live_ssh_install_drift_conflict_retry_and_cleanup(env):
    _, source, _ = env
    connection = ssh_connections.save_connection(
        "acceptance", os.environ["SKILLREG_TEST_SSH_HOST"]
    )
    checked = ssh_connections.check_connection(connection["id"])
    assert checked["status"] == "online", checked
    assert "targets" in ssh_connections.discover(connection["id"])
    args = ssh_connections.ssh_arguments(connection)
    remote_root = subprocess.check_output(
        args + ["mktemp -d /tmp/skillreg-ssh-acceptance-XXXXXXXX"],
        text=True,
        timeout=20,
    ).strip()
    assert (
        remote_root.startswith("/tmp/skillreg-ssh-acceptance-")
        and remote_root.count("/") == 2
    )
    try:
        subprocess.run(
            args + ["mkdir -p " + shlex.quote(remote_root + "/.codex")],
            check=True,
            timeout=20,
        )
        discovered = ssh_connections.discover(connection["id"], remote_root)
        candidate = next(t for t in discovered["targets"] if t["agentKind"] == "codex")
        target = sync_targets.add_target(
            "remote acceptance",
            candidate["path"],
            connection["id"],
            scope="project",
            agent_kind="codex",
            project_root=remote_root,
        )
        runner = CliRunner()

        def execute_cli(*arguments):
            result = runner.invoke(cli, list(arguments))
            assert result.exit_code == 0, result.output
            return json.loads(result.output)

        plan = execute_cli(
            "sync", "preview", "--target-id", target["id"], "--skill", "demo"
        )
        assert plan["targets"][0]["skills"][0]["status"] == "missing"
        first = execute_cli("sync", "execute", "--preview-id", plan["id"])
        assert first["state"] == "succeeded"
        assert execute_cli("sync", "run", first["id"])["state"] == "succeeded"
        inventory = execute_cli("target", "inventory", target["id"])
        assert [item["name"] for item in inventory["skills"]] == ["demo"]
        document = execute_cli("target", "read-skill", target["id"], "demo")
        assert document["content"] == (source / "SKILL.md").read_text()
        repeated = execute_cli(
            "sync", "execute", "--target-id", target["id"], "--skill", "demo"
        )
        assert repeated["results"][0]["skills"][0]["changed"] is False
        stale = sync_runs.preview([target["id"]], ["demo"])
        original = (source / "run.sh").read_bytes()
        (source / "run.sh").write_text("#!/bin/sh\necho remote-edit\n")
        changed, bundle, digest = sync_files.make_bundle(source)
        (source / "run.sh").write_bytes(original)
        ssh_connections.call(
            connection,
            {
                "operation": "install",
                "path": target["path"],
                "name": "demo",
                "bundle": bundle,
                "bundleDigest": digest,
                "sourceDigest": changed["digest"],
                "expectedDigest": stale["targets"][0]["skills"][0]["targetDigest"],
                "force": True,
                "workspaceId": "acceptance",
                "runId": "drift-fixture",
            },
        )
        rejected = sync_runs.create_run(stale["id"], background=False)
        assert rejected["state"] == "failed"
        assert rejected["results"][0]["skills"][0]["error"]["code"] == "target-changed"
        fresh = sync_runs.retry_preview(rejected["id"])
        assert fresh["requiresOverwrite"]
        denied = runner.invoke(cli, ["sync", "execute", "--preview-id", fresh["id"]])
        assert denied.exit_code != 0 and "confirm overwrite" in denied.output
        restored = execute_cli(
            "sync", "execute", "--preview-id", fresh["id"], "--force"
        )
        assert restored["state"] == "succeeded"
        observed = ssh_connections.call(
            connection,
            {"operation": "inspect", "path": target["path"], "names": ["demo"]},
        )
        assert observed["skills"]["demo"] == sync_files.tree_snapshot(source)
        assert len(sync_runs.history()) == 4
        print(
            "SSH_ACCEPTANCE_PASSED",
            json.dumps(
                {
                    "host": connection["host"],
                    "python": checked["details"]["python"],
                    "runId": restored["id"],
                    "status": "synced",
                }
            ),
        )
    finally:
        cleanup = "import shutil,sys; p=sys.argv[1]; assert p.startswith('/tmp/skillreg-ssh-acceptance-') and p.count('/') == 2; shutil.rmtree(p)"
        subprocess.run(
            args
            + ["python3 -c " + shlex.quote(cleanup) + " " + shlex.quote(remote_root)],
            check=True,
            timeout=20,
        )
        print("SSH_ACCEPTANCE_CLEANED", remote_root)
