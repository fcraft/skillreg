#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
hook_src="$repo_root/scripts/hooks/commit-msg"
hook_dst="$repo_root/.git/hooks/commit-msg"

if [[ ! -d "$repo_root/.git" ]]; then
  echo "ERROR: .git directory not found: $repo_root/.git" >&2
  exit 1
fi

cp "$hook_src" "$hook_dst"
chmod +x "$hook_dst"

echo "Installed git hook: .git/hooks/commit-msg"
