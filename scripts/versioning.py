#!/usr/bin/env python3
"""Plan, synchronize, and validate skillreg release versions."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11.
    tomllib = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
RUNTIME_INIT = ROOT / "src" / "skillreg" / "__init__.py"
BUILTIN_SKILL = ROOT / "src" / "skillreg" / "builtin" / "skillreg-skill" / "SKILL.md"
UV_LOCK = ROOT / "uv.lock"
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
TAG_RE = re.compile(r"^v(\d+\.\d+\.\d+)$")
CONVENTIONAL_HEADER_RE = re.compile(
    r"^(?P<type>[a-z][a-z0-9-]*)(?:\([^)]+\))?(?P<breaking>!)?:\s+.+$",
    re.IGNORECASE,
)
RELEASE_COMMIT_RE = re.compile(r"^chore\(release\): v\d+\.\d+\.\d+$", re.IGNORECASE)
BUMP_LEVELS = {"patch": 1, "minor": 2, "major": 3}


class VersionPlanError(RuntimeError):
    """Raised when the repository cannot produce a safe release plan."""


@dataclass(frozen=True)
class CommitTrigger:
    hash: str
    header: str
    bump: str
    reason: str


@dataclass(frozen=True)
class ReleasePlan:
    base_tag: str
    base_version: str
    range: str
    requested_bump: str
    automatic_bump: str | None
    bump: str | None
    override: bool
    current_version: str
    pending_version: str | None
    minimum_version: str | None
    next_version: str | None
    release_required: bool
    triggers: list[CommitTrigger]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def read_pyproject_version(root: Path = ROOT) -> str:
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    if tomllib is None:
        return read_pyproject_version_fallback(text)
    data: dict[str, Any] = tomllib.loads(text)
    return str(data["project"]["version"])


def read_pyproject_version_fallback(text: str) -> str:
    in_project = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "[project]":
            in_project = True
            continue
        if in_project and stripped.startswith("["):
            break
        if not in_project or not stripped.startswith("version"):
            continue
        match = re.match(r'^version\s*=\s*"([^"]+)"\s*$', stripped)
        if match:
            return match.group(1)
    raise RuntimeError("pyproject.toml must define [project].version")


def read_runtime_version(root: Path = ROOT) -> str:
    init_path = root / "src" / "skillreg" / "__init__.py"
    tree = ast.parse(init_path.read_text(encoding="utf-8"), filename=str(init_path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets):
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return node.value.value
    raise RuntimeError("src/skillreg/__init__.py must define string __version__")


def read_builtin_skill_version(root: Path = ROOT) -> str:
    text = _builtin_skill_path(root).read_text(encoding="utf-8")
    frontmatter = _frontmatter(text)
    match = re.search(r'(?m)^  version:\s*"([^"]+)"\s*$', frontmatter)
    if not match:
        raise RuntimeError("builtin skill must define metadata.version")
    return match.group(1)


def read_npm_package_version(root: Path = ROOT) -> str:
    data = json.loads((root / "npm" / "package.json").read_text(encoding="utf-8"))
    return str(data["version"])


def read_npm_lock_versions(root: Path = ROOT) -> tuple[str, str]:
    data = json.loads((root / "npm" / "package-lock.json").read_text(encoding="utf-8"))
    return str(data["version"]), str(data["packages"][""]["version"])


def read_uv_lock_version(root: Path = ROOT) -> str:
    lock_path = root / "uv.lock"
    if tomllib is None:
        return _read_uv_lock_version_fallback(lock_path.read_text(encoding="utf-8"))
    data = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    matches = [
        package
        for package in data.get("package", [])
        if package.get("name") == "skillreg"
        and package.get("source", {}).get("editable") == "."
    ]
    if len(matches) != 1:
        raise RuntimeError("uv.lock must contain exactly one editable skillreg package")
    return str(matches[0]["version"])


def _read_uv_lock_version_fallback(text: str) -> str:
    for block in re.split(r"(?=^\[\[package\]\]\s*$)", text, flags=re.MULTILINE):
        if not re.search(r'(?m)^name = "skillreg"\s*$', block):
            continue
        if not re.search(r'(?m)^source = \{ editable = "\." \}\s*$', block):
            continue
        match = re.search(r'(?m)^version = "([^"]+)"\s*$', block)
        if match:
            return match.group(1)
    raise RuntimeError("uv.lock must contain exactly one editable skillreg package")


def sync_version(version: str, root: Path = ROOT) -> None:
    validate_release_version(version)
    _replace_pyproject_version(version, root)
    _replace_runtime_version(version, root)
    _replace_builtin_skill_version(version, root)
    _replace_npm_versions(version, root)
    _replace_uv_lock_version(version, root)


def check_versions(root: Path = ROOT, require_tag: bool = False) -> list[str]:
    pyproject_version = read_pyproject_version(root)
    runtime_version = read_runtime_version(root)
    builtin_version = read_builtin_skill_version(root)
    npm_version = read_npm_package_version(root)
    npm_lock_version, npm_lock_root_version = read_npm_lock_versions(root)
    uv_lock_version = read_uv_lock_version(root)
    errors: list[str] = []

    if not VERSION_RE.match(pyproject_version):
        errors.append(f"pyproject version must be x.y.z: {pyproject_version}")
    if runtime_version != pyproject_version:
        errors.append(
            "__version__ mismatch: "
            f"src/skillreg/__init__.py has {runtime_version}, "
            f"pyproject.toml has {pyproject_version}"
        )
    if builtin_version != pyproject_version:
        errors.append(
            "builtin skill version mismatch: "
            f"SKILL.md has {builtin_version}, pyproject.toml has {pyproject_version}"
        )
    if npm_version != pyproject_version:
        errors.append(
            f"npm package version mismatch: npm/package.json has {npm_version}, "
            f"pyproject.toml has {pyproject_version}"
        )
    if npm_lock_version != pyproject_version or npm_lock_root_version != pyproject_version:
        errors.append(
            "npm lock version mismatch: "
            f"npm/package-lock.json has {npm_lock_version}/{npm_lock_root_version}, "
            f"pyproject.toml has {pyproject_version}"
        )
    if uv_lock_version != pyproject_version:
        errors.append(
            f"uv lock version mismatch: uv.lock has {uv_lock_version}, "
            f"pyproject.toml has {pyproject_version}"
        )

    if require_tag:
        tag = tag_from_env()
        expected = f"v{pyproject_version}"
        if tag != expected:
            errors.append(f"tag mismatch: expected {expected}, got {tag or '(none)'}")

    return errors


def validate_release_version(version: str) -> None:
    if not VERSION_RE.match(version):
        raise ValueError(f"version must be x.y.z: {version}")


def tag_from_env() -> str | None:
    ref_name = os.environ.get("GITHUB_REF_NAME")
    if ref_name:
        return ref_name
    ref = os.environ.get("GITHUB_REF")
    if ref and ref.startswith("refs/tags/"):
        return ref.removeprefix("refs/tags/")
    return None


def bump_version(version: str, bump: str) -> str:
    validate_release_version(version)
    if bump not in BUMP_LEVELS:
        raise ValueError(f"unsupported bump: {bump}")
    major, minor, patch = (int(part) for part in version.split("."))
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def classify_commit(header: str, body: str) -> tuple[str, str] | None:
    if RELEASE_COMMIT_RE.match(header):
        return None
    match = CONVENTIONAL_HEADER_RE.match(header)
    if not match:
        return None
    commit_type = match.group("type").lower()
    breaking_footer = bool(
        re.search(r"(?im)^BREAKING(?: |-)?CHANGE:\s+\S", body)
    )
    if match.group("breaking") or breaking_footer:
        return "major", "breaking change"
    if commit_type == "feat":
        return "minor", "feat commit"
    if commit_type in {"fix", "perf", "revert"}:
        return "patch", f"{commit_type} commit"
    return None


def find_base_tag(root: Path = ROOT) -> tuple[str, str]:
    tags = _git(["tag", "--list"], root).splitlines()
    if not tags:
        raise VersionPlanError("No Git tags found; fetch release tags before planning a release")

    valid_tags = [(tag, TAG_RE.fullmatch(tag)) for tag in tags]
    semver_tags = [(tag, match.group(1)) for tag, match in valid_tags if match]
    if not semver_tags:
        invalid = ", ".join(sorted(tags))
        raise VersionPlanError(f"No valid SemVer tags found; expected vX.Y.Z, found: {invalid}")

    reachable: list[tuple[int, tuple[int, int, int], str, str]] = []
    for tag, version in semver_tags:
        result = _git_result(["merge-base", "--is-ancestor", f"{tag}^{{}}", "HEAD"], root)
        if result.returncode != 0:
            continue
        distance = int(_git(["rev-list", "--count", f"{tag}^{{}}..HEAD"], root))
        reachable.append((distance, _version_tuple(version), tag, version))

    if not reachable:
        candidates = ", ".join(sorted(tag for tag, _version in semver_tags))
        raise VersionPlanError(
            f"No SemVer tag is reachable from HEAD; reachable history does not contain: {candidates}"
        )

    reachable.sort(key=lambda item: (item[0], tuple(-part for part in item[1])))
    _distance, _version_tuple_value, tag, version = reachable[0]
    tagged_version = _read_version_at_ref(tag, root)
    if tagged_version != version:
        raise VersionPlanError(
            f"Tag {tag} points to package version {tagged_version}, expected {version}"
        )
    return tag, version


def collect_commit_triggers(base_tag: str, root: Path = ROOT) -> list[CommitTrigger]:
    output = _git(
        ["log", "--format=%H%x1f%s%x1f%B%x1e", f"{base_tag}^{{}}..HEAD"],
        root,
    )
    triggers: list[CommitTrigger] = []
    for record in output.split("\x1e"):
        record = record.strip()
        if not record:
            continue
        parts = record.split("\x1f", 2)
        if len(parts) != 3:
            raise VersionPlanError("Unable to parse Git commit history for release planning")
        commit_hash, header, body = parts
        classification = classify_commit(header.strip(), body)
        if classification is None:
            continue
        bump, reason = classification
        triggers.append(
            CommitTrigger(
                hash=commit_hash.strip(),
                header=header.strip(),
                bump=bump,
                reason=reason,
            )
        )
    return triggers


def plan_release(bump: str = "auto", root: Path = ROOT) -> ReleasePlan:
    if bump not in {"auto", *BUMP_LEVELS}:
        raise ValueError(f"unsupported bump mode: {bump}")
    metadata_errors = check_versions(root)
    if metadata_errors:
        raise VersionPlanError("Version metadata is inconsistent: " + "; ".join(metadata_errors))

    base_tag, base_version = find_base_tag(root)
    current_version = read_pyproject_version(root)
    triggers = collect_commit_triggers(base_tag, root)
    automatic_bump = max(
        (trigger.bump for trigger in triggers),
        key=lambda item: BUMP_LEVELS[item],
        default=None,
    )
    override = bump != "auto"
    effective_bump = bump if override else automatic_bump
    current = _version_tuple(current_version)
    base = _version_tuple(base_version)
    if current < base:
        raise VersionPlanError(
            f"Current package version {current_version} is lower than base tag {base_tag}"
        )

    if effective_bump is None:
        return ReleasePlan(
            base_tag=base_tag,
            base_version=base_version,
            range=f"{base_tag}..HEAD",
            requested_bump=bump,
            automatic_bump=automatic_bump,
            bump=None,
            override=False,
            current_version=current_version,
            pending_version=current_version if _version_tuple(current_version) > _version_tuple(base_version) else None,
            minimum_version=None,
            next_version=None,
            release_required=False,
            triggers=triggers,
        )

    minimum_version = bump_version(base_version, effective_bump)
    minimum = _version_tuple(minimum_version)
    pending_version = current_version if current > base else None
    if pending_version and current < minimum:
        raise VersionPlanError(
            f"Pending package version {current_version} is lower than required "
            f"{minimum_version} for {effective_bump} changes in {base_tag}..HEAD"
        )
    next_version = pending_version or minimum_version

    return ReleasePlan(
        base_tag=base_tag,
        base_version=base_version,
        range=f"{base_tag}..HEAD",
        requested_bump=bump,
        automatic_bump=automatic_bump,
        bump=effective_bump,
        override=override,
        current_version=current_version,
        pending_version=pending_version,
        minimum_version=minimum_version,
        next_version=next_version,
        release_required=True,
        triggers=triggers,
    )


def prepare_release(bump: str = "auto", root: Path = ROOT) -> ReleasePlan:
    plan = plan_release(bump, root)
    if not plan.release_required or not plan.next_version:
        raise VersionPlanError(
            f"No releasable changes found in {plan.range}; use --bump patch|minor|major to override"
        )
    sync_version(plan.next_version, root)
    return plan


def _version_tuple(version: str) -> tuple[int, int, int]:
    validate_release_version(version)
    return tuple(int(part) for part in version.split("."))  # type: ignore[return-value]


def _git(args: list[str], root: Path) -> str:
    result = _git_result(args, root)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown Git error"
        raise VersionPlanError(f"Git command failed ({' '.join(args)}): {detail}")
    return result.stdout.strip()


def _git_result(args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def _read_version_at_ref(ref: str, root: Path) -> str:
    text = _git(["show", f"{ref}^{{}}:pyproject.toml"], root)
    try:
        return read_pyproject_version_fallback(text)
    except RuntimeError as exc:
        raise VersionPlanError(f"Cannot read package version from tag {ref}: {exc}") from exc


def _replace_pyproject_version(version: str, root: Path) -> None:
    path = root / "pyproject.toml"
    text = path.read_text(encoding="utf-8")
    updated, count = re.subn(
        r'(?m)^version\s*=\s*"[^"]+"\s*$',
        f'version = "{version}"',
        text,
        count=1,
    )
    if count != 1:
        raise RuntimeError("failed to update pyproject version")
    path.write_text(updated, encoding="utf-8")


def _replace_runtime_version(version: str, root: Path) -> None:
    path = root / "src" / "skillreg" / "__init__.py"
    text = path.read_text(encoding="utf-8")
    updated, count = re.subn(
        r'(?m)^__version__\s*=\s*"[^"]+"\s*$',
        f'__version__ = "{version}"',
        text,
        count=1,
    )
    if count != 1:
        raise RuntimeError("failed to update runtime version")
    path.write_text(updated, encoding="utf-8")


def _replace_builtin_skill_version(version: str, root: Path) -> None:
    path = _builtin_skill_path(root)
    text = path.read_text(encoding="utf-8")
    frontmatter = _frontmatter(text)
    if re.search(r"(?m)^metadata:\s*$", frontmatter):
        updated, count = re.subn(
            r'(?m)^  version:\s*"[^"]+"\s*$',
            f'  version: "{version}"',
            text,
            count=1,
        )
        if count == 0:
            updated = re.sub(
                r"(?m)^metadata:\s*$",
                f'metadata:\n  version: "{version}"',
                text,
                count=1,
            )
    else:
        updated = text.replace(
            "\n---\n",
            f'\nmetadata:\n  version: "{version}"\n---\n',
            1,
        )
    path.write_text(updated, encoding="utf-8")


def _replace_npm_versions(version: str, root: Path) -> None:
    package_path = root / "npm" / "package.json"
    package_data = json.loads(package_path.read_text(encoding="utf-8"))
    package_data["version"] = version
    package_path.write_text(
        json.dumps(package_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    lock_path = root / "npm" / "package-lock.json"
    lock_data = json.loads(lock_path.read_text(encoding="utf-8"))
    lock_data["version"] = version
    lock_data["packages"][""]["version"] = version
    lock_path.write_text(
        json.dumps(lock_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _replace_uv_lock_version(version: str, root: Path) -> None:
    path = root / "uv.lock"
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"(?=^\[\[package\]\]\s*$)", text, flags=re.MULTILINE)
    match_count = 0
    for index, block in enumerate(blocks):
        if not re.search(r'(?m)^name = "skillreg"\s*$', block):
            continue
        if not re.search(r'(?m)^source = \{ editable = "\." \}\s*$', block):
            continue
        updated, count = re.subn(
            r'(?m)^version = "[^"]+"\s*$',
            f'version = "{version}"',
            block,
            count=1,
        )
        if count != 1:
            raise RuntimeError("editable skillreg package in uv.lock has no version")
        blocks[index] = updated
        match_count += 1
    if match_count != 1:
        raise RuntimeError("uv.lock must contain exactly one editable skillreg package")
    path.write_text("".join(blocks), encoding="utf-8")


def _builtin_skill_path(root: Path) -> Path:
    return root / "src" / "skillreg" / "builtin" / "skillreg-skill" / "SKILL.md"


def _frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        raise RuntimeError("builtin SKILL.md must start with YAML frontmatter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise RuntimeError("builtin SKILL.md frontmatter is not closed")
    return parts[1]


def _print_plan(plan: ReleasePlan) -> None:
    print(f"Base tag: {plan.base_tag} ({plan.base_version})")
    print(f"Commit range: {plan.range}")
    print(f"Current version: {plan.current_version}")
    print(f"Automatic bump: {plan.automatic_bump or 'none'}")
    if plan.override:
        print(f"Override bump: {plan.bump}")
    if not plan.release_required:
        print("Release: not required")
        return
    if plan.pending_version:
        print(f"Pending version: {plan.pending_version}")
    print(f"Minimum version: {plan.minimum_version}")
    print(f"Next version: {plan.next_version}")
    print("Triggers:")
    for trigger in plan.triggers:
        print(
            f"  {trigger.hash[:12]} {trigger.header} "
            f"[{trigger.bump}: {trigger.reason}]"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage skillreg release versions.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check", help="Check version consistency.")
    check_parser.add_argument("--require-tag", action="store_true")

    subparsers.add_parser("current", help="Print the current package version.")

    sync_parser = subparsers.add_parser("sync", help="Synchronize all version metadata.")
    sync_parser.add_argument("--version", help="Version to write. Defaults to the current version.")

    plan_parser = subparsers.add_parser("plan", help="Preview the next release version.")
    plan_parser.add_argument("--bump", choices=["auto", *BUMP_LEVELS], default="auto")
    plan_parser.add_argument("--json", action="store_true", dest="as_json")

    prepare_parser = subparsers.add_parser("prepare", help="Synchronize the planned release version.")
    prepare_parser.add_argument("--bump", choices=["auto", *BUMP_LEVELS], default="auto")
    prepare_parser.add_argument("--json", action="store_true", dest="as_json")

    args = parser.parse_args()

    try:
        if args.command == "check":
            errors = check_versions(require_tag=args.require_tag)
            if errors:
                for error in errors:
                    print(f"ERROR: {error}", file=sys.stderr)
                return 1
            print(f"version ok: {read_pyproject_version()}")
            return 0

        if args.command == "current":
            print(read_pyproject_version())
            return 0

        if args.command == "sync":
            version = args.version or read_pyproject_version()
            sync_version(version)
            print(f"version synced: {version}")
            return 0

        if args.command in {"plan", "prepare"}:
            plan = plan_release(args.bump) if args.command == "plan" else prepare_release(args.bump)
            if args.as_json:
                print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2))
            else:
                _print_plan(plan)
            return 0
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
