# skillreg

**skill registry control plane** — manage AI agent skills with a dashboard & CLI.

[![CI](https://github.com/fcraft/skillreg/actions/workflows/ci.yml/badge.svg)](https://github.com/fcraft/skillreg/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![License MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What is skillreg?

skillreg helps you manage your collection of AI agent skills (`SKILL.md` files).

- **Dashboard** — browse skills, sync to targets, view git history, import from zip/git/local
- **CLI** — `skillreg config`, `skillreg dashboard open`, `skillreg workspace create`
- **Sync** — push skills to Claude, CodeBuddy, Codex, and other agent directories
- **Zero Node.js** — pure Python (FastAPI + Click), install with `uv tool install`

## Quick Start

```bash
# Install
uv tool install skillreg

# Create a workspace
skillreg workspace create ~/my-skills

# Open the dashboard
skillreg dashboard open
```

Then open http://127.0.0.1:8787 in your browser.

## Architecture

skillreg uses a **dual-repo model** (PRD §2.1):

```
skillreg/                     # product repo (CLI + API + Dashboard)
├── src/skillreg/             # Python package
├── dashboard/                # Web UI (served by Python backend)
└── specs/                    # Architecture PRD & API contract
```

```
<workspace>/                  # user skills repo (independent git)
├── skills/                   # individual skills
├── repos/                    # submodule-based skills
└── .skillreg/builtin/        # auto-injected skillreg self-skill
```

All configuration lives in `~/.skillreg/config.json` (workspace pointer, targets, agents).

## API

The v1 API contract is frozen in [`specs/api-contract.md`](specs/api-contract.md) and [`specs/openapi.yaml`](specs/openapi.yaml).

Key endpoints:

| Domain | Endpoints |
|--------|-----------|
| Health | `GET /api/health` |
| Skills | `GET /api/skills`, `GET /api/skills/:id`, `GET /api/skills/refresh` |
| Sync | `GET/POST /api/sync/targets`, `POST /api/sync/execute` |
| Import | `POST /api/import/validate`, `/execute`, `/git-clone`, `/git-import` |
| Files | `GET /api/files/tree`, `GET /api/files/content` |
| Git | `GET /api/git/logs` |
| Submodules | `GET /api/submodules`, `POST /api/submodules/sync` |
| Hooks | `GET /api/hooks/scan`, `/status`, `POST /api/hooks/install` |

## Development

```bash
git clone https://github.com/fcraft/skillreg.git
cd skillreg
uv venv
uv pip install -e ".[dev]"
pytest                           # 39 tests
python -m skillreg.cli config    # CLI test
```

## License

MIT — see [LICENSE](LICENSE).
