"""Configuration management for skillreg.

Per PRD §2.3, all skillreg-local state lives in ``~/.skillreg/config.json``:

- ``workspace_path`` — pointer to the workspace repo (skills storage). The
  workspace itself only holds ``skills/`` + ``repos/``; it no longer carries
  ``sync-skills.json`` or ``infra/``.
- ``targets`` — install targets (e.g. ``~/.claude/skills``).
- ``agents`` — agent conventions map (claude / codebuddy / codex …).

Exclude rules and manifest settings stay code-internal (not in this file).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# --- locations -------------------------------------------------------------

CONFIG_DIR: Path = Path.home() / ".skillreg"
CONFIG_FILE: Path = CONFIG_DIR / "config.json"


# --- model -----------------------------------------------------------------


class SkillregConfig(BaseModel):
    """Schema for ``~/.skillreg/config.json``."""

    workspace_path: Optional[str] = Field(
        default=None,
        description="Absolute path to the workspace repo (skills storage). "
        "null until the user configures it.",
    )
    targets: List[str] = Field(
        default_factory=list,
        description="Install targets (agent skill dirs), e.g. ~/.claude/skills.",
    )
    agents: Dict[str, Any] = Field(
        default_factory=dict,
        description="Agent conventions map. Keys are agent names "
        "(claude / codebuddy / codex …); values are agent-specific convention "
        "records (structure expanded in later issues).",
    )


def default_config() -> SkillregConfig:
    """Return a fresh empty config with all expected fields."""
    return SkillregConfig()


# --- I/O -------------------------------------------------------------------


def load_config(path: Optional[Path] = None) -> SkillregConfig:
    """Load config from ``path`` (default: ``~/.skillreg/config.json``).

    If the file does not exist, it is created with the default empty structure
    and returned. The config directory is created on demand.
    """
    if path is None:
        path = CONFIG_FILE
    if not path.exists():
        cfg = default_config()
        save_config(cfg, path)
        return cfg
    data = json.loads(path.read_text(encoding="utf-8"))
    # Coerce into the schema; unknown keys are dropped, missing keys defaulted.
    return SkillregConfig.model_validate(data)


def save_config(cfg: SkillregConfig, path: Optional[Path] = None) -> None:
    """Persist ``cfg`` to ``path`` (default: ``~/.skillreg/config.json``)."""
    if path is None:
        path = CONFIG_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(cfg.model_dump_json(indent=2), encoding="utf-8")
