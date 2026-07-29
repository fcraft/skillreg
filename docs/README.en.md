# skillreg

> A local manager for AI agent skills.

[中文 README](../README.md)

`skillreg` manages local AI agent skills. Register any folder containing
`SKILL.md` into a shared workspace, then sync it to Claude, Codex, CodeBuddy,
`~/.agents/skills`, or other agent skill directories.

## Capabilities

- **CLI**: create/switch workspaces, register/convert skills, manage NPM sources and targets/projects, run sync, inspect diffs, and start the dashboard.
- **Skill**: includes the built-in `skillreg-skill` so agents can find a local `SKILL.md` from any project and register it into the current workspace.
- **Dashboard**: import skills from local folders, ZIP archives, Git, or NPM packages; manage sources and sync targets; and inspect repository status, dependency graphs, and Git history.

## Install

Install with uv:

```bash
uv tool install skillreg
```

Or install through npm:

```bash
npm install --global skillreg
```

The npm launcher runs the exact matching Python package. It uses `uv` when
available, or creates an isolated environment with Python 3.9+ on first use.

Then:

```bash
skillreg workspace create ~/my-skills
skillreg register /path/to/my-skill
skillreg target add ~/.codex/skills
skillreg sync execute --target ~/.codex/skills
skillreg dashboard open
```

For the complete command and option reference:

```bash
skillreg -h
skillreg <group> -h
```

To import NPM skill packages, run `skillreg source npm -h` for preview, import,
and update commands. skillreg downloads and verifies registry artifacts without
running `npm install` or lifecycle scripts.

## Development

```bash
git clone https://github.com/fcraft/skillreg.git
cd skillreg
uv sync --extra dev
scripts/install-git-hooks.sh
uv run pytest -q
uv run --with ruff ruff check src/ tests/ scripts/
```

For a local release:

```bash
scripts/release.sh
```

The script validates version metadata, creates and pushes the tag, and lets
GitHub Actions publish the GitHub Release, PyPI package, and npm package.

## License

[MIT](../LICENSE)
