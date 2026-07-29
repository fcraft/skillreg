#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
hook_src="$repo_root/scripts/hooks/commit-msg"

if ! git_dir="$(git -C "$repo_root" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)"; then
  echo "ERROR: Git repository not found: $repo_root" >&2
  exit 1
fi

hook_dst="$git_dir/hooks/commit-msg"
legacy_hook='#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
commit_msg_file="${1:?commit message file is required}"

python3 "$repo_root/scripts/versioning.py" bump --commit-msg-file "$commit_msg_file"

git add \
  "$repo_root/pyproject.toml" \
  "$repo_root/src/skillreg/__init__.py" \
  "$repo_root/src/skillreg/builtin/skillreg-skill/SKILL.md" \
  "$repo_root/npm/package.json" \
  "$repo_root/npm/package-lock.json"'

if [[ -e "$hook_dst" ]] && ! cmp -s "$hook_src" "$hook_dst"; then
  existing_hook="$(cat "$hook_dst")"
  if [[ "$existing_hook" != "$legacy_hook" ]]; then
    echo "ERROR: refusing to overwrite custom hook: $hook_dst" >&2
    exit 1
  fi
  echo "Replacing legacy skillreg hook: $hook_dst"
fi

mkdir -p "$(dirname "$hook_dst")"
cp "$hook_src" "$hook_dst"
chmod +x "$hook_dst"

echo "Installed Git hook: $hook_dst"
