# skillreg

> A local manager for AI agent skills.

[中文 README](../README.md)

`skillreg` manages local AI agent skills. Register any folder containing
`SKILL.md` into a shared workspace, then sync it to Claude, Codex, CodeBuddy,
`~/.agents/skills`, or other agent skill directories.

## Capabilities

- **CLI**: create/switch workspaces, register/convert skills, manage targets/projects, run sync, inspect diffs, and start the dashboard.
- **Skill**: includes the built-in `skillreg-skill` so agents can find a local `SKILL.md` from any project and register it into the current workspace.
- **Dashboard**: import skills, switch workspaces, manage sync targets, inspect diffs, batch sync by project, and view repository status, dependency graph, and Git history.

## Install

```bash
uv tool install skillreg
skillreg workspace create ~/my-skills
skillreg register /path/to/my-skill
skillreg target add ~/.codex/skills
skillreg sync execute --target ~/.codex/skills
skillreg dashboard open
```

The dashboard opens at:

```text
http://127.0.0.1:28787
```

Common commands:

```bash
skillreg config
skillreg workspace create <path>
skillreg workspace current
skillreg workspace switch <path>
skillreg register <path> [--force] [--name name]
skillreg list
skillreg convert <name>
skillreg target list
skillreg target add <path>
skillreg sync status
skillreg sync execute --target <path> [--skill name]
skillreg project create --name <name> --target <path>
skillreg sync execute --project <name>
skillreg diff <skill> --target <path>
skillreg submodule list
skillreg dashboard start
skillreg dashboard status
skillreg dashboard stop
skillreg dashboard open --no-browser
```

## Development

```bash
git clone https://github.com/fcraft/skillreg.git
cd skillreg
uv sync --extra dev
scripts/install-git-hooks.sh
uv run pytest -q
uv run --with ruff ruff check src/ tests/ scripts/
```

Version metadata is checked across `pyproject.toml`,
`src/skillreg/__init__.py`, and the built-in `skillreg-skill`. After installing
the git hook, commits on `main` automatically bump `x.y.z`: `feat:` increments
`y`, other commits increment `z`, and `x` is fixed to `1`.

Local release:

```bash
scripts/release.sh
```

The script reads the current version, creates and pushes `v<version>`, and lets
GitHub Actions publish the GitHub Release and PyPI package.

## License

[MIT](../LICENSE)
