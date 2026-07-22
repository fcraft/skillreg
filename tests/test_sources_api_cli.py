from __future__ import annotations

import subprocess

from click.testing import CliRunner

import skillreg.config as cfgmod
from skillreg.cli import cli
from skillreg.server import create_app
from skillreg.services import source_manager

from .test_source_manager import PACKAGE, REGISTRY, make_acquired


def configure_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    (workspace / "skills").mkdir(parents=True)
    (workspace / "repos").mkdir()
    subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=workspace, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=workspace, check=True)
    (workspace / "README.md").write_text("workspace\n")
    subprocess.run(["git", "add", "README.md"], cwd=workspace, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=workspace, check=True)
    config = cfgmod.load_config()
    config.workspace_path = str(workspace)
    cfgmod.save_config(config)
    return workspace


def test_sources_api_preview_import_list_check_and_update(tmp_path, monkeypatch):
    configure_workspace(tmp_path)
    packages = iter([
        make_acquired(tmp_path, "1.0.0", {"source-one": {"name": "one"}}),
        make_acquired(tmp_path, "1.0.0", {"source-one": {"name": "one"}}),
        make_acquired(tmp_path, "2.0.0", {"source-one": {"name": "one", "body": "new"}}),
    ])
    monkeypatch.setattr(source_manager, "acquire_package", lambda *args: next(packages))
    from fastapi.testclient import TestClient
    client = TestClient(create_app())

    preview = client.post("/api/sources/npm/preview", json={"package": PACKAGE, "registry": REGISTRY, "versionSpec": "latest"})
    assert preview.status_code == 200, preview.text
    body = preview.json()["data"]
    assert body["skills"][0]["sourceDirectory"] == "source-one"

    imported = client.post("/api/sources/npm/import", json={"token": body["token"], "mode": "skill", "selectedSkills": ["one"]})
    assert imported.status_code == 200, imported.text
    source_id = imported.json()["data"]["source"]["id"]
    assert client.get("/api/sources").json()["data"][0]["id"] == source_id
    assert client.post(f"/api/sources/{source_id}/check").json()["data"]["status"] == "up-to-date"

    diff = client.post(f"/api/sources/{source_id}/update-preview", json={})
    assert diff.status_code == 200, diff.text
    assert diff.json()["data"]["summary"]["modified"] == 1
    updated = client.post(f"/api/sources/{source_id}/update", json={"token": diff.json()["data"]["token"], "force": False})
    assert updated.status_code == 200, updated.text
    assert updated.json()["data"]["status"] == "updated"


def test_sources_api_rejects_invalid_session(tmp_path):
    configure_workspace(tmp_path)
    from fastapi.testclient import TestClient
    response = TestClient(create_app()).post(
        "/api/sources/npm/import",
        json={"token": "not-a-session", "mode": "skill", "selectedSkills": ["one"]},
    )
    assert response.status_code == 400
    assert "preview session" in response.json()["detail"]


def test_source_cli_happy_path_json_and_help(tmp_path, monkeypatch):
    configure_workspace(tmp_path)
    packages = iter([
        make_acquired(tmp_path, "1.0.0", {"source-one": {"name": "one"}}),
        make_acquired(tmp_path, "1.0.0", {"source-one": {"name": "one"}}),
        make_acquired(tmp_path, "1.0.0", {"source-one": {"name": "one"}}),
    ])
    monkeypatch.setattr(source_manager, "acquire_package", lambda *args: next(packages))
    runner = CliRunner()

    imported = runner.invoke(cli, ["source", "npm", "import", PACKAGE, "--registry", REGISTRY, "--skill", "one", "--json"])
    assert imported.exit_code == 0, imported.output
    assert '"resolvedVersion": "1.0.0"' in imported.output
    listed = runner.invoke(cli, ["source", "list", "--json"])
    assert listed.exit_code == 0 and '"package": "@scope/design-skills"' in listed.output
    checked = runner.invoke(cli, ["source", "check", "scope-design-skills", "--json"])
    assert checked.exit_code == 0 and '"status": "up-to-date"' in checked.output
    dry_run = runner.invoke(cli, ["source", "update", "scope-design-skills", "--dry-run", "--json"])
    assert dry_run.exit_code == 0 and '"dryRun": true' in dry_run.output

    for args in (["source", "-h"], ["source", "npm", "-h"], ["source", "npm", "preview", "-h"], ["source", "update", "--help"]):
        result = runner.invoke(cli, args)
        assert result.exit_code == 0, result.output
