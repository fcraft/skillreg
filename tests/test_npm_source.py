from __future__ import annotations

import base64
import hashlib
import io
import json
import tarfile
import pytest

from skillreg.services import npm_source


def make_package_tarball(
    skills: list[tuple[str, str]],
    *,
    package: str = "@tencent/qq-genui-design-basic",
    version: str = "1.2.0",
    extra_members: list[tarfile.TarInfo] | None = None,
    scripts: dict[str, str] | None = None,
) -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        files = {
            "package/package.json": json.dumps({"name": package, "version": version, "scripts": scripts or {}}).encode(),
        }
        for directory, name in skills:
            files[f"package/{directory}/SKILL.md"] = (
                f"---\nname: {name}\ndescription: {name} description\n---\n\n# {name}\n"
            ).encode()
        for name, payload in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
        for info in extra_members or []:
            archive.addfile(info, io.BytesIO(b"x" * info.size) if info.isfile() else None)
    return output.getvalue()


def dist_for(payload: bytes) -> dict[str, str]:
    return {
        "tarball": "https://registry.example/pkg.tgz?token=secret",
        "shasum": hashlib.sha1(payload).hexdigest(),
        "integrity": "sha512-" + base64.b64encode(hashlib.sha512(payload).digest()).decode(),
    }


def test_resolve_scoped_package_and_semver_range():
    metadata = {
        "name": "@scope/pkg",
        "dist-tags": {"latest": "2.0.0", "next": "2.1.0-beta.1"},
        "versions": {
            "1.2.0": {"name": "@scope/pkg", "version": "1.2.0", "dist": {}},
            "1.4.3": {"name": "@scope/pkg", "version": "1.4.3", "dist": {}},
            "2.0.0": {"name": "@scope/pkg", "version": "2.0.0", "dist": {}},
        },
    }

    assert npm_source.metadata_url("@scope/pkg", "https://registry.example/") == (
        "https://registry.example/%40scope%2Fpkg"
    )
    assert npm_source.resolve_version(metadata, "latest")["version"] == "2.0.0"
    assert npm_source.resolve_version(metadata, "^1.2.0")["version"] == "1.4.3"
    assert npm_source.resolve_version(metadata, "~1.2.0")["version"] == "1.2.0"


def test_verify_extract_and_discover_multiple_skills(tmp_path):
    skills = [(f"skill-{index}", f"skill-{index}") for index in range(6)]
    skills.append(("qq-genui-android-ui-code", "html-to-android"))
    payload = make_package_tarball(skills)
    dist = dist_for(payload)

    npm_source.verify_tarball(payload, dist)
    root = npm_source.extract_tarball(payload, tmp_path / "extract")
    discovered = npm_source.discover_skills(
        root,
        expected_package="@tencent/qq-genui-design-basic",
        expected_version="1.2.0",
    )

    assert len(discovered) == 7
    android = next(item for item in discovered if item.name == "html-to-android")
    assert android.source_directory == "qq-genui-android-ui-code"
    assert android.description == "html-to-android description"
    assert npm_source.sanitize_tarball_url(dist["tarball"]) == "https://registry.example/pkg.tgz"


@pytest.mark.parametrize(
    "member",
    [
        tarfile.TarInfo("../escape"),
        tarfile.TarInfo("/absolute"),
        tarfile.TarInfo("C:/windows"),
    ],
)
def test_extract_rejects_unsafe_paths(tmp_path, member):
    member.size = 1
    with pytest.raises(npm_source.NpmSourceError, match="unsafe tar member"):
        npm_source.extract_tarball(make_package_tarball([], extra_members=[member]), tmp_path / "out")


@pytest.mark.parametrize("kind", [tarfile.SYMTYPE, tarfile.LNKTYPE])
def test_extract_rejects_links(tmp_path, kind):
    member = tarfile.TarInfo("package/link")
    member.type = kind
    member.linkname = "../../escape"
    with pytest.raises(npm_source.NpmSourceError, match="links are not allowed"):
        npm_source.extract_tarball(make_package_tarball([], extra_members=[member]), tmp_path / "out")


def test_integrity_and_resource_limits(tmp_path, monkeypatch):
    payload = make_package_tarball([("one", "one")])
    dist = dist_for(payload)
    with pytest.raises(npm_source.NpmSourceError, match="integrity mismatch"):
        npm_source.verify_tarball(payload + b"corrupt", dist)

    monkeypatch.setattr(npm_source.LIMITS, "max_files", 1)
    with pytest.raises(npm_source.NpmSourceError, match="too many files"):
        npm_source.extract_tarball(payload, tmp_path / "limited")

    monkeypatch.setattr(npm_source.LIMITS, "max_files", 10_000)
    monkeypatch.setattr(npm_source.LIMITS, "max_file_bytes", 8)
    with pytest.raises(npm_source.NpmSourceError, match="file size limit"):
        npm_source.extract_tarball(payload, tmp_path / "large-file")

    monkeypatch.setattr(npm_source.LIMITS, "max_file_bytes", 32 * 1024 * 1024)
    monkeypatch.setattr(npm_source.LIMITS, "max_unpacked_bytes", 8)
    with pytest.raises(npm_source.NpmSourceError, match="unpacked size limit"):
        npm_source.extract_tarball(payload, tmp_path / "large-total")

    monkeypatch.setattr(npm_source.LIMITS, "max_tarball_bytes", len(payload) - 1)
    with pytest.raises(npm_source.NpmSourceError, match="compressed size limit"):
        npm_source.verify_tarball(payload, dist)


def test_discovery_rejects_invalid_and_duplicate_names(tmp_path):
    duplicate = make_package_tarball([("first", "same"), ("second", "same")])
    root = npm_source.extract_tarball(duplicate, tmp_path / "duplicate")
    with pytest.raises(npm_source.NpmSourceError, match="duplicate skill name"):
        npm_source.discover_skills(root, "@tencent/qq-genui-design-basic", "1.2.0")

    invalid = make_package_tarball([("first", "../bad")])
    root = npm_source.extract_tarball(invalid, tmp_path / "invalid")
    with pytest.raises(npm_source.NpmSourceError, match="invalid skill name"):
        npm_source.discover_skills(root, "@tencent/qq-genui-design-basic", "1.2.0")


def test_acquire_never_executes_lifecycle_scripts(tmp_path, monkeypatch):
    marker = tmp_path / "lifecycle-ran"
    payload = make_package_tarball(
        [("one", "one")],
        scripts={name: f"touch {marker}" for name in ("preinstall", "install", "postinstall", "prepack", "prepare", "postpack")},
    )
    dist = dist_for(payload)
    metadata = {
        "name": "@tencent/qq-genui-design-basic",
        "dist-tags": {"latest": "1.2.0"},
        "versions": {"1.2.0": {"name": "@tencent/qq-genui-design-basic", "version": "1.2.0", "dist": dist}},
    }
    monkeypatch.setattr(npm_source, "fetch_metadata", lambda *args, **kwargs: metadata)
    monkeypatch.setattr(npm_source, "download_tarball", lambda *args, **kwargs: payload)

    acquired = npm_source.acquire_package("@tencent/qq-genui-design-basic", "latest", "https://registry.example/")
    try:
        assert [skill.name for skill in acquired.skills] == ["one"]
        assert not marker.exists()
    finally:
        acquired.cleanup()
