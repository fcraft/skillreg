"""Secure NPM artifact resolution, verification, extraction and Skill discovery."""

from __future__ import annotations

import base64
import atexit
import hashlib
import json
import re
import shutil
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO

import yaml


class NpmSourceError(ValueError):
    """Raised when an NPM artifact cannot be trusted or interpreted."""


@dataclass
class ResourceLimits:
    max_tarball_bytes: int = 64 * 1024 * 1024
    max_unpacked_bytes: int = 256 * 1024 * 1024
    max_file_bytes: int = 32 * 1024 * 1024
    max_files: int = 10_000


@dataclass(frozen=True)
class DiscoveredSkill:
    name: str
    description: str
    source_directory: str
    file_count: int


@dataclass
class AcquiredPackage:
    package: str
    version_spec: str
    version: str
    registry: str
    tarball: str
    shasum: str | None
    integrity: str
    root: Path
    temp_dir: Path
    skills: list[DiscoveredSkill]

    def cleanup(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        _TEMP_DIRS.discard(self.temp_dir)


LIMITS = ResourceLimits()
_TEMP_DIRS: set[Path] = set()
_SKILL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:[/\\]")
_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$")
_SKIPPED_DIRS = {".git", "node_modules", "__pycache__", "__MACOSX"}


def normalize_registry(registry: str) -> str:
    value = registry.strip()
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise NpmSourceError("registry must be an http or https URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise NpmSourceError("registry must not contain credentials, query or fragment")
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/") + "/", "", ""))


def validate_package_name(package: str) -> str:
    value = package.strip()
    simple = r"[a-z0-9][a-z0-9._~-]*"
    if not re.fullmatch(rf"(?:@{simple}/{simple}|{simple})", value):
        raise NpmSourceError(f"invalid npm package name: {package}")
    return value


def metadata_url(package: str, registry: str) -> str:
    return normalize_registry(registry) + urllib.parse.quote(validate_package_name(package), safe="")


def _version_tuple(value: str) -> tuple[int, int, int, int, str] | None:
    match = _SEMVER_RE.fullmatch(value)
    if not match:
        return None
    major, minor, patch, prerelease = match.groups()
    return int(major), int(minor), int(patch), 0 if prerelease is None else -1, prerelease or ""


def _matches(version: tuple[int, int, int, int, str], spec: str) -> bool:
    major, minor, patch, stable, _ = version
    if stable < 0:
        return False
    if spec in {"", "*", "latest"}:
        return True
    exact = _version_tuple(spec)
    if exact:
        return version == exact
    if spec.startswith("^"):
        base = _version_tuple(spec[1:])
        if not base:
            return False
        upper = (base[0] + 1, 0, 0) if base[0] else ((0, base[1] + 1, 0) if base[1] else (0, 0, base[2] + 1))
        return version[:3] >= base[:3] and version[:3] < upper
    if spec.startswith("~"):
        base = _version_tuple(spec[1:])
        return bool(base and version[:3] >= base[:3] and version[:3] < (base[0], base[1] + 1, 0))
    wildcard = re.fullmatch(r"(\d+)(?:\.(\d+))?\.(?:x|\*)|(?:(\d+)\.(?:x|\*))", spec)
    if wildcard:
        wanted_major = int(wildcard.group(1) or wildcard.group(3))
        wanted_minor = int(wildcard.group(2)) if wildcard.group(2) is not None else None
        return major == wanted_major and (wanted_minor is None or minor == wanted_minor)
    return False


def resolve_version(metadata: dict[str, Any], version_spec: str) -> dict[str, Any]:
    versions = metadata.get("versions")
    if not isinstance(versions, dict):
        raise NpmSourceError("registry metadata is missing versions")
    tags = metadata.get("dist-tags") if isinstance(metadata.get("dist-tags"), dict) else {}
    requested = (version_spec or "latest").strip()
    tagged = tags.get(requested)
    if tagged:
        result = versions.get(tagged)
        if isinstance(result, dict):
            return result
    if requested in versions and isinstance(versions[requested], dict):
        return versions[requested]
    candidates = [
        (parsed, item)
        for version, item in versions.items()
        if isinstance(item, dict) and (parsed := _version_tuple(version)) and _matches(parsed, requested)
    ]
    if not candidates:
        raise NpmSourceError(f"version specifier did not match any published version: {requested}")
    return max(candidates, key=lambda pair: pair[0])[1]


def fetch_metadata(package: str, registry: str, *, timeout: float = 30) -> dict[str, Any]:
    request = urllib.request.Request(
        metadata_url(package, registry),
        headers={"Accept": "application/json", "User-Agent": "skillreg"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read(8 * 1024 * 1024 + 1)
    except (OSError, urllib.error.URLError) as exc:
        raise NpmSourceError(f"cannot fetch npm metadata: {exc}") from exc
    if len(payload) > 8 * 1024 * 1024:
        raise NpmSourceError("npm metadata is too large")
    try:
        data = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NpmSourceError("npm registry returned invalid JSON") from exc
    if not isinstance(data, dict) or data.get("name") != validate_package_name(package):
        raise NpmSourceError("npm registry returned an unexpected package")
    return data


def _read_limited(stream: BinaryIO, limit: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = stream.read(min(1024 * 1024, limit + 1 - size))
        if not chunk:
            break
        chunks.append(chunk)
        size += len(chunk)
        if size > limit:
            raise NpmSourceError("npm tarball exceeds compressed size limit")
    return b"".join(chunks)


def download_tarball(url: str, *, timeout: float = 120) -> bytes:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise NpmSourceError("tarball URL must use http or https")
    request = urllib.request.Request(url, headers={"User-Agent": "skillreg"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return _read_limited(response, LIMITS.max_tarball_bytes)
    except NpmSourceError:
        raise
    except (OSError, urllib.error.URLError) as exc:
        detail = str(exc).replace(url, sanitize_tarball_url(url))
        raise NpmSourceError(f"cannot download npm tarball: {detail}") from exc


def verify_tarball(payload: bytes, dist: dict[str, Any]) -> None:
    if len(payload) > LIMITS.max_tarball_bytes:
        raise NpmSourceError("npm tarball exceeds compressed size limit")
    integrity = str(dist.get("integrity") or "")
    verified = False
    for token in integrity.split():
        algorithm, separator, encoded = token.partition("-")
        if not separator or algorithm.lower() not in hashlib.algorithms_available:
            continue
        actual = base64.b64encode(hashlib.new(algorithm.lower(), payload).digest()).decode()
        if actual == encoded:
            verified = True
            break
    if not verified:
        raise NpmSourceError("tarball integrity mismatch")
    shasum = dist.get("shasum")
    if shasum and hashlib.sha1(payload).hexdigest().lower() != str(shasum).lower():
        raise NpmSourceError("tarball shasum mismatch")


def _safe_member_parts(name: str) -> tuple[str, ...]:
    if not name or "\\" in name or _WINDOWS_DRIVE_RE.match(name) or any(ord(char) < 32 for char in name):
        raise NpmSourceError(f"unsafe tar member: {name}")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise NpmSourceError(f"unsafe tar member: {name}")
    parts = tuple(part for part in path.parts if part not in {"", "."})
    if not parts:
        raise NpmSourceError(f"unsafe tar member: {name}")
    return parts


def extract_tarball(payload: bytes, destination: Path) -> Path:
    destination = destination.resolve()
    if destination.exists():
        raise NpmSourceError(f"extraction destination already exists: {destination}")
    destination.mkdir(parents=True)
    total_size = 0
    file_count = 0
    try:
        with tarfile.open(fileobj=__import__("io").BytesIO(payload), mode="r:gz") as archive:
            for member in archive:
                parts = _safe_member_parts(member.name)
                target = destination.joinpath(*parts)
                if member.issym() or member.islnk():
                    raise NpmSourceError(f"links are not allowed in tarball: {member.name}")
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                if not member.isfile():
                    raise NpmSourceError(f"unsupported tar member: {member.name}")
                file_count += 1
                if file_count > LIMITS.max_files:
                    raise NpmSourceError("tarball contains too many files")
                if member.size > LIMITS.max_file_bytes:
                    raise NpmSourceError(f"tar member exceeds file size limit: {member.name}")
                total_size += member.size
                if total_size > LIMITS.max_unpacked_bytes:
                    raise NpmSourceError("tarball exceeds unpacked size limit")
                source = archive.extractfile(member)
                if source is None:
                    raise NpmSourceError(f"cannot read tar member: {member.name}")
                target.parent.mkdir(parents=True, exist_ok=True)
                remaining = member.size
                with target.open("xb") as output:
                    while remaining:
                        chunk = source.read(min(1024 * 1024, remaining))
                        if not chunk:
                            raise NpmSourceError(f"truncated tar member: {member.name}")
                        output.write(chunk)
                        remaining -= len(chunk)
        package_root = destination / "package"
        if not package_root.is_dir():
            raise NpmSourceError("tarball does not contain package/ root")
        return package_root
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise


def _frontmatter(skill_md: Path) -> dict[str, Any]:
    try:
        text = skill_md.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise NpmSourceError(f"cannot read {skill_md.name}") from exc
    if not text.startswith("---"):
        raise NpmSourceError(f"missing frontmatter in {skill_md}")
    parts = text.split("---", 2)
    try:
        value = yaml.safe_load(parts[1]) if len(parts) == 3 else None
    except yaml.YAMLError as exc:
        raise NpmSourceError(f"invalid frontmatter in {skill_md}") from exc
    if not isinstance(value, dict):
        raise NpmSourceError(f"invalid frontmatter in {skill_md}")
    return value


def discover_skills(root: Path, expected_package: str, expected_version: str) -> list[DiscoveredSkill]:
    try:
        identity = json.loads((root / "package.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise NpmSourceError("extracted package has invalid package.json") from exc
    if identity.get("name") != expected_package or identity.get("version") != expected_version:
        raise NpmSourceError("extracted package identity does not match registry metadata")
    results: list[DiscoveredSkill] = []
    names: set[str] = set()
    for skill_md in sorted(root.rglob("SKILL.md")):
        rel_parts = skill_md.relative_to(root).parts
        if any(part.startswith(".") or part in _SKIPPED_DIRS for part in rel_parts[:-1]):
            continue
        fm = _frontmatter(skill_md)
        name = str(fm.get("name") or "")
        if not _SKILL_NAME_RE.fullmatch(name):
            raise NpmSourceError(f"invalid skill name in {skill_md.relative_to(root)}: {name}")
        if name in names:
            raise NpmSourceError(f"duplicate skill name in package: {name}")
        names.add(name)
        directory = skill_md.parent
        file_count = sum(1 for path in directory.rglob("*") if path.is_file())
        results.append(DiscoveredSkill(name, str(fm.get("description") or ""), directory.relative_to(root).as_posix(), file_count))
    if not results:
        raise NpmSourceError("npm package does not contain any valid SKILL.md")
    return results


def sanitize_tarball_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    hostname = parsed.hostname or ""
    netloc = hostname
    if parsed.port:
        netloc += f":{parsed.port}"
    return urllib.parse.urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))


def acquire_package(package: str, version_spec: str, registry: str) -> AcquiredPackage:
    package = validate_package_name(package)
    registry = normalize_registry(registry)
    metadata = fetch_metadata(package, registry)
    resolved = resolve_version(metadata, version_spec)
    version = str(resolved.get("version") or "")
    if resolved.get("name") != package or not _version_tuple(version):
        raise NpmSourceError("resolved npm metadata has an invalid package identity")
    dist = resolved.get("dist")
    if not isinstance(dist, dict) or not dist.get("tarball") or not dist.get("integrity"):
        raise NpmSourceError("resolved npm metadata is missing tarball integrity")
    payload = download_tarball(str(dist["tarball"]))
    verify_tarball(payload, dist)
    temp_dir = Path(tempfile.mkdtemp(prefix="skillreg-npm-", dir=tempfile.gettempdir())).resolve()
    _TEMP_DIRS.add(temp_dir)
    try:
        root = extract_tarball(payload, temp_dir / "extracted")
        skills = discover_skills(root, package, version)
        return AcquiredPackage(
            package=package,
            version_spec=version_spec or "latest",
            version=version,
            registry=registry,
            tarball=sanitize_tarball_url(str(dist["tarball"])),
            shasum=str(dist["shasum"]) if dist.get("shasum") else None,
            integrity=str(dist["integrity"]),
            root=root,
            temp_dir=temp_dir,
            skills=skills,
        )
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        _TEMP_DIRS.discard(temp_dir)
        raise


@atexit.register
def _cleanup_temp_dirs() -> None:
    for path in list(_TEMP_DIRS):
        shutil.rmtree(path, ignore_errors=True)
        _TEMP_DIRS.discard(path)
