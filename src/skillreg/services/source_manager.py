"""NPM source lifecycle shared by the API, CLI and Dashboard."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from .git_ops import commit_exact, init_repo, run_git, worktree_dirty
from .npm_source import AcquiredPackage, NpmSourceError, acquire_package
from .source_store import SourceStore, validate_relative_path


class SourceManagerError(ValueError):
    """Raised when a managed source operation is unsafe or invalid."""


_SESSION_TTL = 30 * 60
_SESSIONS: dict[str, tuple[float, AcquiredPackage, str | None, Path]] = {}
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _slug(package: str) -> str:
    value = package.lower().replace("@", "").replace("/", "-")
    value = re.sub(r"[^a-z0-9_-]+", "-", value).strip("-")
    if not value or not _ID_RE.fullmatch(value):
        raise SourceManagerError(f"cannot derive a safe source id from package: {package}")
    return value


def _file_hashes(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    result = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            result[relative] = f"symlink:{os.readlink(path)}"
        elif path.is_file():
            result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _diff(before: dict[str, str], after: dict[str, str], prefix: str) -> list[dict[str, str]]:
    files = []
    for path in sorted(before.keys() | after.keys()):
        if path not in before:
            status = "added"
        elif path not in after:
            status = "deleted"
        elif before[path] != after[path]:
            status = "modified"
        else:
            status = "unchanged"
        files.append({"path": f"{prefix}/{path}" if path else prefix, "status": status})
    order = {"modified": 0, "added": 1, "deleted": 2, "unchanged": 3}
    return sorted(files, key=lambda item: (order[item["status"]], item["path"]))


def _summary(files: list[dict[str, str]]) -> dict[str, int]:
    return {status: sum(item["status"] == status for item in files) for status in ("added", "modified", "deleted", "unchanged")}


def _copy_tree(source: Path, target: Path) -> None:
    shutil.copytree(source, target, copy_function=shutil.copy2)


def _manifest(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "source": {
            "type": "npm",
            "package": record["package"],
            "versionSpec": record["versionSpec"],
            "version": record["resolvedVersion"],
            "registry": record["registry"],
            "tarball": record.get("tarball", ""),
            "shasum": record.get("shasum"),
            "integrity": record["integrity"],
            "updated_at": record["updatedAt"],
        },
        "skills": [
            {
                "source_directory": item["sourceDirectory"],
                "repository_directory": PurePosixPath(item["targetDirectory"]).relative_to(record["targetPath"]).as_posix(),
                "name": item["name"],
            }
            for item in record["skills"]
        ],
    }


def load_repo_manifest(repo: Path) -> dict[str, Any]:
    path = repo.expanduser().resolve() / "source-manifest.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceManagerError(f"cannot read source-manifest.json: {exc}") from exc
    source = data.get("source") if isinstance(data, dict) else None
    skills = data.get("skills") if isinstance(data, dict) else None
    if not isinstance(source, dict) or source.get("type") != "npm" or not isinstance(skills, list) or not skills:
        raise SourceManagerError("source-manifest.json is missing npm source or skill mappings")
    converted = {
        "package": source.get("package"),
        "registry": source.get("registry"),
        "versionSpec": source.get("versionSpec") or source.get("version") or "latest",
        "resolvedVersion": source.get("resolvedVersion") or source.get("version"),
        "tarball": source.get("tarball", ""),
        "shasum": source.get("shasum"),
        "integrity": source.get("integrity"),
        "skills": [],
    }
    if not all(converted.get(key) for key in ("package", "registry", "resolvedVersion", "integrity")):
        raise SourceManagerError("source-manifest.json has incomplete source metadata")
    names: set[str] = set()
    for item in skills:
        source_dir = item.get("sourceDirectory") or item.get("source_directory")
        target_dir = item.get("targetDirectory") or item.get("repository_directory")
        name = item.get("name")
        if not source_dir or not target_dir or not name or name in names:
            raise SourceManagerError("source-manifest.json has an invalid skill mapping")
        source_path = PurePosixPath(str(source_dir))
        if source_path.is_absolute() or ".." in source_path.parts or "\\" in str(source_dir):
            raise SourceManagerError("source-manifest.json has an unsafe source directory")
        names.add(name)
        validate_relative_path(str(target_dir), prefixes=("skills",))
        converted["skills"].append({"sourceDirectory": source_dir, "targetDirectory": target_dir, "name": name})
    return converted


class SourceManager:
    def __init__(self, workspace: Path, *, acquire: Callable[[str, str, str], AcquiredPackage] | None = None):
        self.workspace = workspace.expanduser().resolve()
        if not self.workspace.is_dir():
            raise SourceManagerError(f"workspace directory not found: {self.workspace}")
        self.store = SourceStore(self.workspace)
        self.acquire = acquire or acquire_package

    def _session(self, package: AcquiredPackage, source_id: str | None = None) -> str:
        self._prune_sessions()
        token = uuid.uuid4().hex
        _SESSIONS[token] = (time.monotonic() + _SESSION_TTL, package, source_id, self.workspace)
        return token

    def _take_session(self, token: str, source_id: str | None = None, *, consume: bool = True) -> AcquiredPackage:
        self._prune_sessions()
        entry = _SESSIONS.get(token)
        if not entry or entry[3] != self.workspace or (source_id is not None and entry[2] != source_id):
            raise SourceManagerError("preview session is missing, expired or belongs to another source")
        if consume:
            _SESSIONS.pop(token, None)
        return entry[1]

    @staticmethod
    def _prune_sessions() -> None:
        now = time.monotonic()
        for token, (expires, package, _, _) in list(_SESSIONS.items()):
            if expires <= now:
                package.cleanup()
                _SESSIONS.pop(token, None)

    def discard_preview(self, token: str) -> None:
        acquired = self._take_session(token, consume=True)
        acquired.cleanup()

    def preview_npm(self, package: str, registry: str, version_spec: str = "latest") -> dict[str, Any]:
        acquired = self.acquire(package, version_spec or "latest", registry)
        token = self._session(acquired)
        skills = []
        for skill in acquired.skills:
            target = f"skills/{skill.name}"
            skills.append({
                "name": skill.name,
                "description": skill.description,
                "sourceDirectory": skill.source_directory,
                "defaultTargetDirectory": target,
                "fileCount": skill.file_count,
                "conflict": (self.workspace / target).exists(),
            })
        return {
            "token": token,
            "package": acquired.package,
            "versionSpec": acquired.version_spec,
            "resolvedVersion": acquired.version,
            "registry": acquired.registry,
            "integrity": acquired.integrity,
            "shasum": acquired.shasum,
            "skills": skills,
        }

    def list_sources(self) -> list[dict[str, Any]]:
        result = []
        for source in self.store.list():
            item = dict(source)
            if item["mode"] == "repo":
                repo = self.workspace / item["targetPath"]
                item["remoteConfigured"] = bool((repo / ".git").exists() and run_git(repo, ["remote"], check=False).stdout.strip())
            result.append(item)
        return result

    def _source_id(self, package: str, target_path: str) -> str:
        base = _slug(package)
        existing = self.store.list()
        for record in existing:
            if record["package"] == package and record["targetPath"] == target_path:
                return record["id"]
        used = {record["id"] for record in existing}
        if base not in used:
            return base
        suffix = hashlib.sha256(target_path.encode()).hexdigest()[:8]
        return f"{base}-{suffix}"

    def import_npm(
        self,
        token: str,
        mode: str,
        selected_skills: list[str],
        *,
        target_path: str | None = None,
        force: bool = False,
        remote: str | None = None,
        branch: str | None = None,
    ) -> dict[str, Any]:
        acquired = self._take_session(token)
        try:
            if mode not in {"skill", "repo"}:
                raise SourceManagerError("mode must be skill or repo")
            selected = self._select(acquired, selected_skills)
            default_id = _slug(acquired.package)
            if mode == "skill":
                base = validate_relative_path(target_path or "skills", prefixes=("skills",))
                mappings = [(skill, f"{base}/{skill.name}") for skill in selected]
                source_target = base
            else:
                source_target = validate_relative_path(target_path or f"repos/{default_id}", prefixes=("repos",))
                if len(PurePosixPath(source_target).parts) < 2:
                    raise SourceManagerError("repo target must be below repos/")
                mappings = [(skill, f"{source_target}/skills/{skill.name}") for skill in selected]
            source_id = self._source_id(acquired.package, source_target)
            self._ensure_import_conflicts(mappings, force=force, repo_mode=mode == "repo")
            imported_at = _now()
            record = self._record(source_id, acquired, mode, source_target, mappings, imported_at, imported_at)
            if mode == "skill":
                self._apply_skill_import(acquired, record, force)
                remote_configured = False
            else:
                remote_configured = self._apply_repo_import(acquired, record, remote, branch)
            return {"source": record, "imported": record["skills"], "remoteConfigured": remote_configured}
        finally:
            acquired.cleanup()

    @staticmethod
    def _select(acquired: AcquiredPackage, selected_skills: list[str]) -> list[Any]:
        requested = list(dict.fromkeys(selected_skills))
        if not requested:
            raise SourceManagerError("select at least one skill")
        by_name = {skill.name: skill for skill in acquired.skills}
        missing = [name for name in requested if name not in by_name]
        if missing:
            raise SourceManagerError(f"selected skills were not found in package: {', '.join(missing)}")
        return [by_name[name] for name in requested]

    def _ensure_import_conflicts(self, mappings: list[tuple[Any, str]], *, force: bool, repo_mode: bool) -> None:
        if repo_mode:
            return
        conflicts = [target for _, target in mappings if (self.workspace / target).exists()]
        if conflicts and not force:
            raise SourceManagerError(f"target already exists: {', '.join(conflicts)}")

    def _record(self, source_id: str, acquired: AcquiredPackage, mode: str, target: str, mappings: list[tuple[Any, str]], imported: str, updated: str) -> dict[str, Any]:
        return {
            "id": source_id,
            "type": "npm",
            "package": acquired.package,
            "registry": acquired.registry,
            "versionSpec": acquired.version_spec,
            "resolvedVersion": acquired.version,
            "tarball": acquired.tarball,
            "shasum": acquired.shasum,
            "integrity": acquired.integrity,
            "mode": mode,
            "targetPath": target,
            "skills": [
                {
                    "sourceDirectory": skill.source_directory,
                    "targetDirectory": target_dir,
                    "name": skill.name,
                    "fileHashes": _file_hashes(acquired.root / skill.source_directory),
                }
                for skill, target_dir in mappings
            ],
            "importedAt": imported,
            "updatedAt": updated,
        }

    def _transaction_dir(self) -> Path:
        root = self.workspace / ".skillreg"
        root.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(prefix=".transaction-", dir=root))

    def _apply_skill_import(self, acquired: AcquiredPackage, record: dict[str, Any], force: bool) -> None:
        transaction = self._transaction_dir()
        backups: list[tuple[Path, Path]] = []
        created: list[Path] = []
        old_store = self.store.path.read_bytes() if self.store.path.exists() else None
        try:
            for index, mapping in enumerate(record["skills"]):
                target = self.workspace / mapping["targetDirectory"]
                prepared = transaction / "prepared" / str(index)
                _copy_tree(acquired.root / mapping["sourceDirectory"], prepared)
                if target.exists():
                    if not force:
                        raise SourceManagerError(f"target already exists: {mapping['targetDirectory']}")
                    backup = transaction / "backup" / str(index)
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(target, backup)
                    backups.append((target, backup))
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(prepared, target)
                created.append(target)
            self.store.put(record)
            commit_exact(self.workspace, [*(item["targetDirectory"] for item in record["skills"]), ".skillreg/sources.json"], f"feat: import npm source {record['id']}")
        except Exception:
            self._rollback(created, backups, old_store)
            raise
        finally:
            shutil.rmtree(transaction, ignore_errors=True)
        from .skill_registry import clear_cache
        clear_cache(self.workspace)

    def _apply_repo_import(self, acquired: AcquiredPackage, record: dict[str, Any], remote: str | None, branch: str | None) -> bool:
        repo = self.workspace / record["targetPath"]
        repo_existed = repo.exists()
        newly_added_submodule = False
        gitmodules = self.workspace / ".gitmodules"
        old_gitmodules = gitmodules.read_bytes() if gitmodules.exists() else None
        if remote and repo.exists():
            raise SourceManagerError("remote can only be used when creating a new repo target")
        if remote and not repo.exists():
            if branch and (branch.startswith("-") or ".." in branch or not re.fullmatch(r"[A-Za-z0-9._/-]+", branch)):
                raise SourceManagerError("invalid Git branch")
            args = ["submodule", "add"]
            if branch:
                args.extend(["-b", branch])
            args.extend(["--", remote, record["targetPath"]])
            run_git(self.workspace, args)
            newly_added_submodule = True
        repo.mkdir(parents=True, exist_ok=True)
        init_repo(repo)
        old_head_result = run_git(repo, ["rev-parse", "HEAD"], check=False)
        old_repo_head = old_head_result.stdout.strip() if old_head_result.returncode == 0 else ""
        if worktree_dirty(repo) and any(repo.iterdir()):
            existing_manifest = repo / "source-manifest.json"
            unmanaged = run_git(repo, ["status", "--porcelain", "--untracked-files=all"]).stdout.splitlines()
            allowed_prefixes = ("?? source-manifest.json", "?? skills/", "?? README.md")
            if existing_manifest.exists() or any(not line.startswith(allowed_prefixes) for line in unmanaged):
                raise SourceManagerError("repo working tree is not clean; commit or stash changes before importing")
        if (repo / "source-manifest.json").exists():
            existing = load_repo_manifest(repo)
            if existing["package"] != record["package"]:
                raise SourceManagerError("existing repo manifest belongs to another npm package")
            expected_mappings = {
                (
                    item["sourceDirectory"],
                    PurePosixPath(item["targetDirectory"]).relative_to(record["targetPath"]).as_posix(),
                    item["name"],
                )
                for item in record["skills"]
            }
            existing_mappings = {
                (item["sourceDirectory"], item["targetDirectory"], item["name"])
                for item in existing["skills"]
            }
            if existing_mappings != expected_mappings:
                raise SourceManagerError("existing repo manifest skill mappings do not match the selected package skills")
        transaction = self._transaction_dir()
        backups: list[tuple[Path, Path]] = []
        created: list[Path] = []
        old_store = self.store.path.read_bytes() if self.store.path.exists() else None
        manifest_path = repo / "source-manifest.json"
        old_manifest = manifest_path.read_bytes() if manifest_path.exists() else None
        readme = repo / "README.md"
        readme_existed = readme.exists()
        try:
            for index, mapping in enumerate(record["skills"]):
                target = self.workspace / mapping["targetDirectory"]
                prepared = transaction / "prepared" / str(index)
                _copy_tree(acquired.root / mapping["sourceDirectory"], prepared)
                if target.exists():
                    backup = transaction / "backup" / str(index)
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(target, backup)
                    backups.append((target, backup))
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(prepared, target)
                created.append(target)
            manifest_path.write_text(json.dumps(_manifest(record), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            if not readme.exists():
                readme.write_text(f"# {repo.name}\n\nSkills managed from `{record['package']}` by skillreg\n", encoding="utf-8")
            repo_paths = [PurePosixPath(item["targetDirectory"]).relative_to(record["targetPath"]).as_posix() for item in record["skills"]]
            repo_paths.extend(["source-manifest.json", "README.md"])
            commit_exact(repo, repo_paths, f"feat: import npm source {record['id']}")
            self.store.put(record)
            workspace_paths = [".skillreg/sources.json"]
            if newly_added_submodule:
                workspace_paths.extend([record["targetPath"], ".gitmodules"])
            elif (repo / ".git").is_file():
                workspace_paths.append(record["targetPath"])
            commit_exact(self.workspace, workspace_paths, f"feat: register npm source {record['id']}")
        except Exception:
            self._rollback(created, backups, old_store)
            if not repo_existed:
                self._remove_failed_repo(record["targetPath"], repo, newly_added_submodule, old_gitmodules)
            else:
                if old_manifest is None:
                    manifest_path.unlink(missing_ok=True)
                else:
                    manifest_path.write_bytes(old_manifest)
                if not readme_existed:
                    readme.unlink(missing_ok=True)
                self._restore_repo_head(repo, old_repo_head)
                if (repo / ".git").is_file():
                    run_git(self.workspace, ["add", "-A", "--", record["targetPath"], ".skillreg/sources.json"], check=False)
            raise
        finally:
            shutil.rmtree(transaction, ignore_errors=True)
        from .skill_registry import clear_cache
        clear_cache(self.workspace)
        return bool(run_git(repo, ["remote"], check=False).stdout.strip())

    def _remove_failed_repo(self, target_path: str, repo: Path, submodule: bool, old_gitmodules: bytes | None) -> None:
        if submodule:
            run_git(self.workspace, ["submodule", "deinit", "-f", "--", target_path], check=False)
            run_git(self.workspace, ["rm", "-f", "--cached", "--", target_path], check=False)
            modules_path = self.workspace / ".git" / "modules" / Path(target_path)
            shutil.rmtree(modules_path, ignore_errors=True)
        shutil.rmtree(repo, ignore_errors=True)
        gitmodules = self.workspace / ".gitmodules"
        if old_gitmodules is None:
            gitmodules.unlink(missing_ok=True)
        else:
            gitmodules.write_bytes(old_gitmodules)
        run_git(self.workspace, ["add", "-A", "--", target_path, ".gitmodules", ".skillreg/sources.json"], check=False)

    @staticmethod
    def _restore_repo_head(repo: Path, old_head: str) -> None:
        current_result = run_git(repo, ["rev-parse", "HEAD"], check=False)
        current = current_result.stdout.strip() if current_result.returncode == 0 else ""
        if current and current != old_head:
            if old_head:
                run_git(repo, ["update-ref", "HEAD", old_head, current])
                run_git(repo, ["read-tree", old_head])
            else:
                run_git(repo, ["update-ref", "-d", "HEAD", current])
                run_git(repo, ["read-tree", "--empty"])

    def _rollback(self, created: list[Path], backups: list[tuple[Path, Path]], old_store: bytes | None) -> None:
        for path in reversed(created):
            if path.exists():
                shutil.rmtree(path)
        for target, backup in reversed(backups):
            if backup.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(backup, target)
        if old_store is None:
            self.store.path.unlink(missing_ok=True)
        else:
            self.store.path.parent.mkdir(parents=True, exist_ok=True)
            self.store.path.write_bytes(old_store)

    def check(self, source_id: str) -> dict[str, Any]:
        record = self.store.get(source_id)
        try:
            acquired = self.acquire(record["package"], record["versionSpec"], record["registry"])
        except (NpmSourceError, OSError) as exc:
            return {"id": source_id, "status": "check-failed", "currentVersion": record["resolvedVersion"], "error": str(exc)}
        try:
            status = "up-to-date" if acquired.version == record["resolvedVersion"] else "update-available"
            return {"id": source_id, "status": status, "currentVersion": record["resolvedVersion"], "latestVersion": acquired.version}
        finally:
            acquired.cleanup()

    def update_preview(self, source_id: str, version_spec: str | None = None) -> dict[str, Any]:
        record = self.store.get(source_id)
        acquired = self.acquire(record["package"], version_spec or record["versionSpec"], record["registry"])
        try:
            by_name = {skill.name: skill for skill in acquired.skills}
            files: list[dict[str, str]] = []
            local_modified = False
            for mapping in record["skills"]:
                if mapping["name"] not in by_name:
                    raise SourceManagerError(f"updated package is missing managed skill: {mapping['name']}")
                current = _file_hashes(self.workspace / mapping["targetDirectory"])
                expected_current = mapping.get("fileHashes") or {}
                local_modified = local_modified or current != expected_current
                candidate = _file_hashes(acquired.root / by_name[mapping["name"]].source_directory)
                files.extend(_diff(current, candidate, mapping["targetDirectory"]))
            changed = [item for item in files if item["status"] != "unchanged"]
            status = "up-to-date" if acquired.version == record["resolvedVersion"] and not changed else "update-available"
            repo_dirty = record["mode"] == "repo" and worktree_dirty(self.workspace / record["targetPath"])
            token = self._session(acquired, source_id)
            return {
                "id": source_id,
                "token": token,
                "status": status,
                "currentVersion": record["resolvedVersion"],
                "resolvedVersion": acquired.version,
                "localModified": local_modified,
                "repoDirty": repo_dirty,
                "summary": _summary(files),
                "files": changed,
            }
        except Exception:
            acquired.cleanup()
            raise

    def update(self, source_id: str, token: str, *, force: bool = False, dry_run: bool = False) -> dict[str, Any]:
        acquired = self._take_session(token, source_id, consume=False)
        record = self.store.get(source_id)
        by_name = {skill.name: skill for skill in acquired.skills}
        files: list[dict[str, str]] = []
        local_modified = False
        mappings = []
        for mapping in record["skills"]:
            skill = by_name.get(mapping["name"])
            if not skill:
                raise SourceManagerError(f"updated package is missing managed skill: {mapping['name']}")
            current = _file_hashes(self.workspace / mapping["targetDirectory"])
            local_modified = local_modified or current != (mapping.get("fileHashes") or {})
            files.extend(_diff(current, _file_hashes(acquired.root / skill.source_directory), mapping["targetDirectory"]))
            mappings.append((skill, mapping["targetDirectory"]))
        changed = [item for item in files if item["status"] != "unchanged"]
        if dry_run:
            _SESSIONS.pop(token, None)
            acquired.cleanup()
            return {"id": source_id, "dryRun": True, "status": "up-to-date" if not changed and acquired.version == record["resolvedVersion"] else "update-available", "summary": _summary(files), "files": changed}
        if local_modified and not force:
            raise SourceManagerError("managed paths contain local modifications; review the diff and retry with force")
        if record["mode"] == "repo" and worktree_dirty(self.workspace / record["targetPath"]):
            raise SourceManagerError("repo working tree is not clean; commit or stash changes before updating")
        _SESSIONS.pop(token, None)
        try:
            if not changed and acquired.version == record["resolvedVersion"]:
                return {"id": source_id, "dryRun": False, "status": "up-to-date", "summary": _summary(files), "files": []}
            updated = self._record(source_id, acquired, record["mode"], record["targetPath"], mappings, record["importedAt"], _now())
            if record["mode"] == "skill":
                self._replace_update(acquired, updated, repo=None)
            else:
                self._replace_update(acquired, updated, repo=self.workspace / record["targetPath"])
            return {"id": source_id, "dryRun": False, "status": "updated", "resolvedVersion": acquired.version, "summary": _summary(files), "files": changed}
        finally:
            acquired.cleanup()

    def _replace_update(self, acquired: AcquiredPackage, updated: dict[str, Any], repo: Path | None) -> None:
        transaction = self._transaction_dir()
        backups: list[tuple[Path, Path]] = []
        created: list[Path] = []
        old_store = self.store.path.read_bytes()
        manifest_path = repo / "source-manifest.json" if repo else None
        old_manifest = manifest_path.read_bytes() if manifest_path and manifest_path.exists() else None
        old_repo_head = ""
        if repo:
            old_head_result = run_git(repo, ["rev-parse", "HEAD"], check=False)
            old_repo_head = old_head_result.stdout.strip() if old_head_result.returncode == 0 else ""
        try:
            for index, mapping in enumerate(updated["skills"]):
                prepared = transaction / "prepared" / str(index)
                _copy_tree(acquired.root / mapping["sourceDirectory"], prepared)
                target = self.workspace / mapping["targetDirectory"]
                backup = transaction / "backup" / str(index)
                backup.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    os.replace(target, backup)
                    backups.append((target, backup))
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(prepared, target)
                created.append(target)
            if manifest_path:
                manifest_path.write_text(json.dumps(_manifest(updated), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self.store.put(updated)
            if repo:
                repo_paths = [PurePosixPath(item["targetDirectory"]).relative_to(updated["targetPath"]).as_posix() for item in updated["skills"]]
                commit_exact(repo, [*repo_paths, "source-manifest.json"], f"chore: update npm source {updated['id']} to {updated['resolvedVersion']}")
                workspace_paths = [".skillreg/sources.json"]
                git_marker = repo / ".git"
                if git_marker.is_file():
                    workspace_paths.append(updated["targetPath"])
                commit_exact(self.workspace, workspace_paths, f"chore: update npm source {updated['id']}")
            else:
                commit_exact(self.workspace, [*(item["targetDirectory"] for item in updated["skills"]), ".skillreg/sources.json"], f"chore: update npm source {updated['id']} to {updated['resolvedVersion']}")
        except Exception:
            self._rollback(created, backups, old_store)
            if manifest_path:
                if old_manifest is None:
                    manifest_path.unlink(missing_ok=True)
                else:
                    manifest_path.write_bytes(old_manifest)
            if repo:
                self._restore_repo_head(repo, old_repo_head)
            raise
        finally:
            shutil.rmtree(transaction, ignore_errors=True)
        from .skill_registry import clear_cache
        clear_cache(self.workspace)
