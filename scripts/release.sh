#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

dry_run=false
assume_yes=false
bump="auto"

usage() {
  echo "Usage: scripts/release.sh [--dry-run] [--bump auto|patch|minor|major] [--yes]"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      dry_run=true
      shift
      ;;
    --yes)
      assume_yes=true
      shift
      ;;
    --bump)
      if [[ $# -lt 2 ]]; then
        echo "ERROR: --bump requires a value" >&2
        exit 2
      fi
      bump="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$bump" in
  auto|patch|minor|major) ;;
  *)
    echo "ERROR: invalid --bump value: $bump" >&2
    exit 2
    ;;
esac

branch="$(git branch --show-current)"
if [[ "$branch" != "main" ]]; then
  echo "ERROR: releases must run from main; current branch: ${branch:-detached HEAD}" >&2
  exit 1
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "ERROR: origin remote is not configured" >&2
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: working tree is not clean; commit or stash changes before release" >&2
  git status --short >&2
  exit 1
fi

echo "Release plan"
python3 scripts/versioning.py plan --bump "$bump"
plan_json="$(python3 scripts/versioning.py plan --bump "$bump" --json)"
release_required="$(python3 -c 'import json,sys; print(str(json.load(sys.stdin)["release_required"]).lower())' <<<"$plan_json")"
if [[ "$release_required" != "true" ]]; then
  echo "ERROR: automatic release stopped because the commit range has no releasable changes" >&2
  echo "Use --bump patch|minor|major only when an explicit release override is intended" >&2
  exit 1
fi

base_tag="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["base_tag"])' <<<"$plan_json")"
version="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["next_version"])' <<<"$plan_json")"
current_version="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["current_version"])' <<<"$plan_json")"
tag="v$version"

if git rev-parse --verify --quiet "refs/tags/$tag" >/dev/null; then
  echo "ERROR: tag already exists locally: $tag" >&2
  exit 1
fi

echo
echo "Release state"
python3 scripts/check_release_state.py --base-tag "$base_tag" --version "$version"

if [[ "$dry_run" == "true" ]]; then
  echo
  echo "Dry run complete: no files, commits, tags, or remotes were changed"
  exit 0
fi

if [[ "$assume_yes" != "true" ]]; then
  if [[ ! -t 0 ]]; then
    echo "ERROR: release confirmation requires a terminal; pass --yes for intentional automation" >&2
    exit 1
  fi
  read -r -p "Prepare, validate, commit, tag, and push $tag? [y/N] " answer
  if [[ "$answer" != "y" && "$answer" != "Y" ]]; then
    echo "Release cancelled"
    exit 1
  fi
fi

python3 scripts/versioning.py prepare --bump "$bump"

(cd dashboard && npm ci && npm test && npm run build)
uv run python scripts/check_version.py
uv run pytest -q
uv run --with ruff ruff check src/ tests/ scripts/
(cd dashboard && npm run e2e)
(cd npm && npm ci && npm test && npm pack --dry-run)

version_files=(
  pyproject.toml
  src/skillreg/__init__.py
  src/skillreg/builtin/skillreg-skill/SKILL.md
  npm/package.json
  npm/package-lock.json
  uv.lock
)
git add -- "${version_files[@]}"

staged_files="$(git diff --cached --name-only)"
expected_files="$(printf '%s\n' "${version_files[@]}" | sort)"
if [[ -n "$staged_files" ]] && [[ "$(printf '%s\n' "$staged_files" | sort)" != "$expected_files" ]]; then
  echo "ERROR: staged release files do not match the six managed version files" >&2
  git diff --cached --name-status >&2
  exit 1
fi
if [[ "$current_version" != "$version" ]] && [[ -z "$staged_files" ]]; then
  echo "ERROR: preparing $version did not update the managed version files" >&2
  exit 1
fi
git diff --cached --check

git commit --allow-empty -m "chore(release): $tag"
git tag -a "$tag" -m "Release $tag"
git push --atomic origin main "$tag"

echo "Release pushed: $tag"
echo "GitHub Actions will publish the GitHub Release, PyPI package, and npm package"
