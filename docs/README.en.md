# skillreg

> A local manager for AI agent skills.

[中文 README](../README.md)

`skillreg` manages local AI agent skills. Register any folder containing
`SKILL.md` into a shared workspace, then sync it to Claude, Codex, CodeBuddy,
`~/.agents/skills`, or other agent skill directories.

## Capabilities

- **CLI**: create a workspace, inspect current config, and start the dashboard.
- **Skill**: includes the built-in `skillreg-skill` so agents know how to register, import, sync, and troubleshoot skills.
- **Dashboard**: import skills, switch workspaces, manage sync targets, inspect diffs, batch sync by project, and view repository status, dependency graph, and Git history.

## Install

```bash
uv tool install skillreg
skillreg workspace create ~/my-skills
skillreg dashboard open
```

The dashboard opens at:

```text
http://127.0.0.1:8787
```

Common commands:

```bash
skillreg config
skillreg workspace create <path>
skillreg dashboard open --no-browser
```

## Development

```bash
git clone https://github.com/fcraft/skillreg.git
cd skillreg
uv sync --extra dev
uv run pytest -q
uv run --with ruff ruff check src/ tests/ scripts/
```

See [release-process.md](release-process.md) for release notes.

## License

[MIT](../LICENSE)
