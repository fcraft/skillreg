# skillreg

> A local control plane for AI agent skills.

[Back to Chinese README](../README.md)

## What is skillreg?

`skillreg` helps you manage local AI agent skills.

Write a skill with `SKILL.md` in any project, register it into a dedicated skill
workspace, and sync it to Claude, Codex, CodeBuddy, `~/.agents/skills`, or other
agent skill directories.

## Dashboard

The dashboard is the main way to operate `skillreg` day to day:

- **Skills**: browse skills, filter by type, open details, and import local skills
- **Sync**: manage targets, discover agent skill directories under `~/`, install, sync, uninstall, and inspect diffs
- **Projects**: group multiple targets and batch install or sync by project
- **Repositories**: inspect submodule / repo status and check remote state
- **Dependency graph**: view relationships between skills and repositories
- **Git logs**: inspect workspace and repository commit history
- **Command palette**: use `Cmd/Ctrl + K` to jump pages, refresh data, and locate skills
- **Workspace switcher**: switch the active workspace from the header
- **Component playground**: inspect dashboard UI components for development

## Quick Start

```bash
uv tool install skillreg
skillreg workspace create ~/my-skills
skillreg dashboard open
```

The dashboard opens at:

```text
http://127.0.0.1:8787
```

## Common Commands

```bash
skillreg config
skillreg workspace create <path>
skillreg dashboard open
skillreg dashboard open --no-browser
```

## Workspace Layout

```text
<workspace>/
├── skills/                  # standalone skills
├── repos/                   # repo / CLI backed skills
└── .skillreg/builtin/       # built-in skillreg skill
```

Config lives at:

```text
~/.skillreg/config.json
```

## Development

```bash
git clone https://github.com/fcraft/skillreg.git
cd skillreg
uv venv
uv pip install -e ".[dev]"
uv pip install ruff build
python scripts/check_version.py
python -m pytest -q
ruff check src/ tests/ scripts/
```

## Release

See [release-process.md](release-process.md). `pyproject.toml` is the version
source of truth, and CI checks `__version__`, Git tags, and package metadata.

## License

[MIT](../LICENSE)
