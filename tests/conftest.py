"""Shared pytest isolation for skillreg tests."""

from __future__ import annotations

import pytest

import skillreg.config as cfgmod
import skillreg.cli as climod
from skillreg.server import health as health_api


@pytest.fixture(autouse=True)
def isolate_skillreg_config(tmp_path, monkeypatch):
    """Keep tests from reading or writing the user's real ~/.skillreg config."""
    cfg_path = tmp_path / ".skillreg" / "config.json"
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", cfg_path.parent)
    monkeypatch.setattr(cfgmod, "CONFIG_FILE", cfg_path)
    monkeypatch.setattr(climod, "CONFIG_FILE", cfg_path)
    monkeypatch.setattr(health_api, "CONFIG_FILE", cfg_path)
