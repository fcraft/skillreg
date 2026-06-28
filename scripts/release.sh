#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: working tree is not clean; commit or stash changes before release" >&2
  git status --short >&2
  exit 1
fi

uv run python scripts/check_version.py
version="$(uv run python scripts/versioning.py current)"
tag="v$version"

if git rev-parse "$tag" >/dev/null 2>&1; then
  echo "ERROR: tag already exists locally: $tag" >&2
  exit 1
fi

if git ls-remote --exit-code --tags origin "refs/tags/$tag" >/dev/null 2>&1; then
  echo "ERROR: tag already exists on origin: $tag" >&2
  exit 1
fi

git tag -a "$tag" -m "Release $tag"
git push origin main
git push origin "$tag"

echo "Release tag pushed: $tag"
echo "GitHub Actions will publish the package from the tag workflow."
