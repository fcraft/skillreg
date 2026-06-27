# skillreg

skillreg — skill registry control plane. A Python CLI + FastAPI backend that
manages a skill registry (workspace repository of `SKILL.md` skills) and syncs
skills to agent install targets.

> **Status:** M1 skeleton (greenfield). See `specs/skillreg-v2.md` for the full
> architecture PRD and `issues/` for the milestone breakdown.

## Layout (PRD §2.1)

```
skillreg/
├── src/skillreg/        # Python package: CLI + FastAPI backend
├── dashboard/           # Vue frontend build output (placeholder in M1)
├── skillreg-cli/        # submodule: companion CLI (placeholder)
├── self-skill/          # submodule: skillreg self-describing skill (placeholder)
├── ui-framework/        # submodule: UI style framework (placeholder, v1.x)
├── specs/               # PRD + API contract
├── issues/              # milestone issues
└── pyproject.toml       # monorepo root package
```

The **workspace** (skills storage) is a separate git repository pointed to by
`~/.skillreg/config.json::workspace_path`. It only holds `skills/` + `repos/`.

## Install (dev)

```bash
uv venv
uv pip install -e .
skillreg config            # prints config status; auto-creates ~/.skillreg/config.json
skillreg dashboard open    # starts FastAPI backend + opens browser
```

## Configuration (`~/.skillreg/config.json`)

Per PRD §2.3, all skillreg-local state lives here (the workspace repo holds
only `skills/` + `repos/`):

```json
{
  "workspace_path": null,
  "targets": [],
  "agents": {}
}
```

- `workspace_path` — pointer to the workspace repo (null until configured).
- `targets` — install targets (e.g. `~/.claude/skills`).
- `agents` — agent conventions map (claude / codebuddy / codex …).
