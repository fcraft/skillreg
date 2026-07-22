from __future__ import annotations

import json

import pytest

from skillreg.services.source_store import SourceStore, SourceStoreError


def record() -> dict:
    return {
        "id": "scope-pkg",
        "type": "npm",
        "package": "@scope/pkg",
        "registry": "https://registry.example/",
        "versionSpec": "latest",
        "resolvedVersion": "1.0.0",
        "tarball": "https://registry.example/pkg.tgz",
        "shasum": "abc",
        "integrity": "sha512-abc",
        "mode": "skill",
        "targetPath": "skills",
        "skills": [
            {
                "sourceDirectory": "source-one",
                "targetDirectory": "skills/one",
                "name": "one",
                "fileHashes": {"SKILL.md": "abc"},
            }
        ],
        "importedAt": "2026-07-22T00:00:00Z",
        "updatedAt": "2026-07-22T00:00:00Z",
    }


def test_store_round_trip_and_atomic_replace(tmp_path, monkeypatch):
    store = SourceStore(tmp_path)
    seen = []
    monkeypatch.setattr(store, "_replace", lambda src, dst: (seen.append((src, dst)), src.replace(dst)))

    store.put(record())

    assert store.list()[0]["package"] == "@scope/pkg"
    assert seen and seen[0][1] == tmp_path / ".skillreg" / "sources.json"
    assert json.loads(store.path.read_text())["schemaVersion"] == 1


@pytest.mark.parametrize("target", ["../outside", "/tmp/outside", "skills/../../outside"])
def test_store_rejects_workspace_escape(tmp_path, target):
    item = record()
    item["skills"][0]["targetDirectory"] = target
    with pytest.raises(SourceStoreError, match="unsafe relative path"):
        SourceStore(tmp_path).put(item)


def test_store_reports_corrupt_data(tmp_path):
    store = SourceStore(tmp_path)
    store.path.parent.mkdir(parents=True)
    store.path.write_text("{not json", encoding="utf-8")
    with pytest.raises(SourceStoreError, match="cannot read source store"):
        store.list()


def test_store_rejects_mapping_outside_source_target(tmp_path):
    item = record()
    item["targetPath"] = "skills/managed"
    item["skills"][0]["targetDirectory"] = "skills/other/one"
    with pytest.raises(SourceStoreError, match="outside its source target"):
        SourceStore(tmp_path).put(item)
