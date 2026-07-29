"""Derived Dashboard catalog relationships for sources, repositories, and skills."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .source_store import SourceStore, SourceStoreError


def _skill_reference(
    mapping: dict[str, Any],
    skills_by_path: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    target_path = mapping["targetDirectory"]
    skill = skills_by_path.get(target_path)
    return {
        "name": mapping["name"],
        "path": target_path,
        "available": skill is not None,
        "skillId": skill["id"] if skill else None,
    }


def project_catalog(
    workspace: Path,
    registry_data: dict[str, Any],
    *,
    sources: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Add derived catalog relationships without mutating registry cache data."""
    result = deepcopy(registry_data)
    skills_by_path = {skill["path"]: skill for skill in result["skills"]}
    submodules_by_path = {item["path"]: item for item in result["submodules"]}
    repositories: dict[str, dict[str, Any]] = {}

    for submodule in result["submodules"]:
        path = submodule["path"]
        repositories[path] = {
            **submodule,
            "name": path.removeprefix("repos/"),
            "kind": "submodule",
            "exists": (workspace / path).is_dir(),
            "source": None,
            "skills": [
                {
                    "name": skill["name"],
                    "path": skill["path"],
                    "available": True,
                    "skillId": skill["id"],
                }
                for skill in result["skills"]
                if skill.get("submodulePath") == path
            ],
        }

    if sources is None:
        try:
            sources = SourceStore(workspace).list()
        except SourceStoreError:
            sources = []
    source_by_skill_path: dict[str, dict[str, Any]] = {}
    for source in sources:
        source_summary = {
            "id": source["id"],
            "package": source["package"],
            "resolvedVersion": source["resolvedVersion"],
            "mode": source["mode"],
            "targetPath": source["targetPath"],
        }
        for mapping in source["skills"]:
            source_by_skill_path[mapping["targetDirectory"]] = source_summary

        if source["mode"] != "repo":
            continue

        path = source["targetPath"]
        submodule = submodules_by_path.get(path)
        child_skills = [
            _skill_reference(mapping, skills_by_path)
            for mapping in source["skills"]
        ]
        repository = repositories.get(path)
        if repository is None:
            remote_url = next(
                (
                    skill.get("remoteUrl")
                    for skill in result["skills"]
                    if skill.get("submodulePath") == path and skill.get("remoteUrl")
                ),
                None,
            )
            repository = {
                "path": path,
                "name": path.removeprefix("repos/"),
                "kind": "nested",
                "exists": (workspace / path).is_dir(),
                "remoteUrl": remote_url,
                "branch": None,
                "description": f"由 {source['package']} 管理",
                "status": None,
                "source": source_summary,
                "skills": child_skills,
            }
            repositories[path] = repository
        else:
            repository["source"] = source_summary
            repository["skills"] = child_skills
            repository["exists"] = (workspace / path).is_dir()
            if submodule:
                repository["kind"] = "submodule"

    for skill in result["skills"]:
        repository_path = skill.get("submodulePath")
        repository = repositories.get(repository_path) if repository_path else None
        skill["repositoryPath"] = repository_path
        skill["repositoryKind"] = repository["kind"] if repository else None
        skill["source"] = source_by_skill_path.get(skill["path"])

    existing_repo_nodes = {node["path"] for node in result["repoNodes"]}
    for repository in repositories.values():
        if (
            repository["path"] in existing_repo_nodes
            or not any(skill["available"] for skill in repository["skills"])
        ):
            continue
        result["repoNodes"].append({
            "id": repository["path"],
            "name": repository["name"],
            "description": repository["description"],
            "type": "repo-skill",
            "graphType": "repo-skill",
            "parentNode": None,
            "path": repository["path"],
            "skillFilePath": None,
            "fileCount": 0,
            "remoteUrl": repository["remoteUrl"],
            "parentSkill": None,
            "isSubmodule": False,
            "submodulePath": repository["path"],
            "repositoryPath": repository["path"],
            "repositoryKind": repository["kind"],
            "isSubmoduleRoot": False,
            "isRepositoryRoot": True,
            "branch": repository["branch"],
            "source": repository["source"],
        })

    result["repoNodes"].sort(key=lambda item: item["name"].lower())
    result["repositories"] = sorted(
        repositories.values(),
        key=lambda item: item["name"].lower(),
    )
    return result


def enrich_sources(
    workspace: Path,
    sources: list[dict[str, Any]],
    registry_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Attach safe navigation targets to persisted source records."""
    catalog = project_catalog(workspace, registry_data, sources=sources)
    skills_by_path = {skill["path"]: skill for skill in catalog["skills"]}
    repositories = {item["path"]: item for item in catalog["repositories"]}
    enriched = []
    for source in sources:
        item = deepcopy(source)
        item["skills"] = [
            {
                **mapping,
                **_skill_reference(mapping, skills_by_path),
            }
            for mapping in source["skills"]
        ]
        repository = repositories.get(source["targetPath"])
        item["repository"] = (
            {
                "path": repository["path"],
                "name": repository["name"],
                "kind": repository["kind"],
                "exists": repository["exists"],
            }
            if source["mode"] == "repo" and repository
            else None
        )
        enriched.append(item)
    return enriched
