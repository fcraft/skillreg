"""Atomic persistence for workspace-managed external sources."""

from __future__ import annotations

import json
import os
import re
import tempfile
import urllib.parse
from pathlib import Path, PurePosixPath
from typing import Any


class SourceStoreError(ValueError):
    """Raised when persisted source data is invalid or unreadable."""


_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def validate_relative_path(value: str, *, prefixes: tuple[str, ...] = ("skills", "repos")) -> str:
    if not value or "\\" in value or re.match(r"^[A-Za-z]:", value):
        raise SourceStoreError(f"unsafe relative path: {value}")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.parts[0] not in prefixes:
        raise SourceStoreError(f"unsafe relative path: {value}")
    return path.as_posix()


class SourceStore:
    schema_version = 1

    def __init__(self, workspace: Path):
        self.workspace = workspace.expanduser().resolve()
        self.path = self.workspace / ".skillreg" / "sources.json"
        self._replace = os.replace

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schemaVersion": self.schema_version, "sources": []}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SourceStoreError(f"cannot read source store: {exc}") from exc
        if not isinstance(data, dict) or data.get("schemaVersion") != self.schema_version or not isinstance(data.get("sources"), list):
            raise SourceStoreError("cannot read source store: unsupported or invalid schema")
        for item in data["sources"]:
            self._validate(item)
        return data

    def _validate(self, item: Any) -> None:
        if not isinstance(item, dict) or not _ID_RE.fullmatch(str(item.get("id") or "")):
            raise SourceStoreError("invalid source id")
        required = {
            "type", "package", "registry", "versionSpec", "resolvedVersion", "tarball",
            "shasum", "integrity", "mode", "targetPath", "skills", "importedAt", "updatedAt",
        }
        if not required.issubset(item) or item.get("type") != "npm" or item.get("mode") not in {"skill", "repo"}:
            raise SourceStoreError(f"invalid source record: {item.get('id', '<unknown>')}")
        registry = urllib.parse.urlsplit(str(item["registry"]))
        if registry.scheme not in {"http", "https"} or not registry.netloc or registry.username or registry.password:
            raise SourceStoreError("invalid source registry")
        if not all(str(item.get(key) or "") for key in ("package", "versionSpec", "resolvedVersion", "integrity", "importedAt", "updatedAt")):
            raise SourceStoreError("source record has incomplete npm metadata")
        validate_relative_path(str(item["targetPath"]), prefixes=("skills", "repos"))
        target_path = PurePosixPath(str(item["targetPath"]))
        if item["mode"] == "skill" and target_path.parts[0] != "skills":
            raise SourceStoreError("skill source target must be below skills/")
        if item["mode"] == "repo" and (target_path.parts[0] != "repos" or len(target_path.parts) < 2):
            raise SourceStoreError("repo source target must be below repos/")
        skills = item.get("skills")
        if not isinstance(skills, list) or not skills:
            raise SourceStoreError("source record must contain skill mappings")
        names: set[str] = set()
        for mapping in skills:
            if not isinstance(mapping, dict):
                raise SourceStoreError("invalid skill mapping")
            name = str(mapping.get("name") or "")
            if not _ID_RE.fullmatch(name) or name in names:
                raise SourceStoreError(f"invalid or duplicate skill mapping: {name}")
            names.add(name)
            source = str(mapping.get("sourceDirectory") or "")
            source_path = PurePosixPath(source)
            if not source or source_path.is_absolute() or ".." in source_path.parts or "\\" in source:
                raise SourceStoreError(f"unsafe relative path: {source}")
            mapping_target = PurePosixPath(validate_relative_path(str(mapping.get("targetDirectory") or "")))
            required_prefix = target_path.parts + (("skills",) if item["mode"] == "repo" else ())
            if mapping_target.parts[:len(required_prefix)] != required_prefix or len(mapping_target.parts) <= len(required_prefix):
                raise SourceStoreError(f"skill mapping is outside its source target: {mapping_target}")
            hashes = mapping.get("fileHashes")
            if not isinstance(hashes, dict) or not all(isinstance(path, str) and isinstance(digest, str) for path, digest in hashes.items()):
                raise SourceStoreError(f"invalid file hashes for skill mapping: {name}")

    def list(self) -> list[dict[str, Any]]:
        return list(self._read()["sources"])

    def get(self, source_id: str) -> dict[str, Any]:
        for item in self.list():
            if item["id"] == source_id:
                return item
        raise SourceStoreError(f"source not found: {source_id}")

    def put(self, record: dict[str, Any]) -> dict[str, Any]:
        self._validate(record)
        data = self._read()
        data["sources"] = [item for item in data["sources"] if item["id"] != record["id"]] + [record]
        data["sources"].sort(key=lambda item: item["id"])
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".sources-", suffix=".json", dir=self.path.parent)
        temp_path = Path(temporary)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            self._replace(temp_path, self.path)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise
        return record
