from __future__ import annotations

from skillreg.services.catalog import enrich_sources, project_catalog
from skillreg.services.skill_registry import get_all
from skillreg.services.source_store import SourceStore


def _write_skill(path, name):
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Managed skill\n---\n\n# {name}\n",
        encoding="utf-8",
    )


def _source_record(name="managed-skill"):
    return {
        "id": "demo-package",
        "type": "npm",
        "package": "@demo/package",
        "registry": "https://registry.npmjs.org/",
        "versionSpec": "latest",
        "resolvedVersion": "1.2.3",
        "tarball": "https://registry.npmjs.org/demo/-/demo-1.2.3.tgz",
        "shasum": None,
        "integrity": "sha512-demo",
        "mode": "repo",
        "targetPath": "repos/demo-package",
        "skills": [{
            "sourceDirectory": f"skills/{name}",
            "targetDirectory": f"repos/demo-package/skills/{name}",
            "name": name,
            "fileHashes": {"SKILL.md": "abc"},
        }],
        "importedAt": "2026-07-29T00:00:00+00:00",
        "updatedAt": "2026-07-29T00:00:00+00:00",
    }


def test_catalog_projects_nested_npm_repo_and_bidirectional_links(tmp_path):
    repo = tmp_path / "repos" / "demo-package"
    (repo / ".git").mkdir(parents=True)
    _write_skill(repo / "skills" / "managed-skill", "managed-skill")
    SourceStore(tmp_path).put(_source_record())

    data = project_catalog(tmp_path, get_all(tmp_path))

    assert data["repositories"] == [{
        "path": "repos/demo-package",
        "name": "demo-package",
        "kind": "nested",
        "exists": True,
        "remoteUrl": None,
        "branch": None,
        "description": "由 @demo/package 管理",
        "status": None,
        "source": {
            "id": "demo-package",
            "package": "@demo/package",
            "resolvedVersion": "1.2.3",
            "mode": "repo",
            "targetPath": "repos/demo-package",
        },
        "skills": [{
            "name": "managed-skill",
            "path": "repos/demo-package/skills/managed-skill",
            "available": True,
            "skillId": "managed-skill",
        }],
    }]
    skill = data["skills"][0]
    assert skill["repositoryPath"] == "repos/demo-package"
    assert skill["repositoryKind"] == "nested"
    assert skill["source"]["id"] == "demo-package"
    assert any(node["path"] == "repos/demo-package" for node in data["repoNodes"])


def test_source_navigation_does_not_resolve_a_deduped_skill_at_another_path(tmp_path):
    repo = tmp_path / "repos" / "demo-package"
    (repo / ".git").mkdir(parents=True)
    _write_skill(repo / "skills" / "managed-skill", "managed-skill")
    _write_skill(tmp_path / "skills" / "managed-skill", "managed-skill")
    record = SourceStore(tmp_path).put(_source_record())

    enriched = enrich_sources(tmp_path, [record], get_all(tmp_path))

    assert enriched[0]["skills"][0]["available"] is False
    assert enriched[0]["skills"][0]["skillId"] is None
