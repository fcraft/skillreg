from __future__ import annotations

import os
import tempfile
from pathlib import Path

import skillreg.config as cfgmod
import uvicorn

from skillreg.server import create_app
from skillreg.services import sync_manager


def prepare_workspace(root: Path) -> tuple[Path, Path]:
    workspace = root / "workspace"
    skill_dir = workspace / "skills" / "demo-skill"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: Demo skill for dashboard e2e\n---\n\n# demo\n",
        encoding="utf-8",
    )
    (skill_dir / "notes.md").write_text("hello dashboard\n", encoding="utf-8")

    target = root / "targets" / "claude-skills"
    target.mkdir(parents=True, exist_ok=True)
    return workspace, target


def configure_app(temp_root: Path) -> None:
    workspace, target = prepare_workspace(temp_root)

    cfgmod.CONFIG_DIR = temp_root / "config"
    cfgmod.CONFIG_FILE = cfgmod.CONFIG_DIR / "config.json"
    sync_manager._PROJECTS_DIR = temp_root / "state"
    sync_manager._PROJECTS_FILE = sync_manager._PROJECTS_DIR / "projects.json"
    cfg = cfgmod.load_config()
    cfg.workspace_path = str(workspace)
    cfg.targets = [str(target)]
    cfgmod.save_config(cfg)

    os.environ["SKILLREG_DASHBOARD_DIR"] = str(Path(__file__).resolve().parents[2] / "dashboard" / "dist")


def main() -> None:
    temp_root = Path(tempfile.mkdtemp(prefix="skillreg-dashboard-e2e-"))
    configure_app(temp_root)
    app = create_app()
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")


if __name__ == "__main__":
    main()
