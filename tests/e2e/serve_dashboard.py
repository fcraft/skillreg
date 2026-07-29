from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

import uvicorn

import skillreg.config as cfgmod
from skillreg.server import create_app
from skillreg.services import sync_manager


def prepare_workspace(root: Path) -> tuple[Path, Path]:
    workspace = root / "workspace"
    skill_fixtures = [
        ("skills/demo-skill", "demo-skill", "Demo skill for dashboard e2e"),
        ("skills/demo-skill-tools", "demo-skill-tools", "Companion utilities for demos"),
        ("skills/build-page", "build-page", "Build a dashboard page"),
        ("skills/ntdev-build", "ntdev-build", "Build and install Android artifacts"),
        ("skills/sync-helper", "sync-helper", "同步本地 Skill 数据"),
        (
            "repos/third/mattpocock-skills/skills/engineering/ask-matt",
            "ask-matt",
            "Ask Matt for engineering guidance",
        ),
    ]
    for relative_path, name, description in skill_fixtures:
        skill_dir = workspace / relative_path
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n",
            encoding="utf-8",
        )
    (workspace / "skills" / "demo-skill" / "notes.md").write_text(
        "hello dashboard\n",
        encoding="utf-8",
    )
    npm_repo = workspace / "repos" / "npm-design"
    npm_skill = npm_repo / "skills" / "npm-design"
    npm_skill.mkdir(parents=True)
    (npm_skill / "SKILL.md").write_text(
        "---\nname: npm-design\ndescription: NPM managed design skill\n---\n\n# npm-design\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=npm_repo, check=True)
    submodule_repo = workspace / "repos" / "submodule-design"
    submodule_skill = submodule_repo / "skills" / "submodule-design"
    submodule_skill.mkdir(parents=True)
    (submodule_skill / "SKILL.md").write_text(
        "---\nname: submodule-design\ndescription: Submodule managed design skill\n---\n\n# submodule-design\n",
        encoding="utf-8",
    )
    (submodule_repo / ".git").write_text(
        "gitdir: ../../.git/modules/repos/submodule-design\n",
        encoding="utf-8",
    )
    source_store = workspace / ".skillreg" / "sources.json"
    source_store.parent.mkdir()
    source_store.write_text(
        json.dumps({
            "schemaVersion": 1,
            "sources": [{
                "id": "npm-design",
                "type": "npm",
                "package": "@demo/npm-design",
                "registry": "https://registry.npmjs.org/",
                "versionSpec": "latest",
                "resolvedVersion": "1.2.3",
                "tarball": "https://registry.npmjs.org/demo/-/npm-design-1.2.3.tgz",
                "shasum": None,
                "integrity": "sha512-demo",
                "mode": "repo",
                "targetPath": "repos/npm-design",
                "skills": [{
                    "sourceDirectory": "skills/npm-design",
                    "targetDirectory": "repos/npm-design/skills/npm-design",
                    "name": "npm-design",
                    "fileHashes": {"SKILL.md": "demo"},
                }],
                "importedAt": "2026-07-29T00:00:00+00:00",
                "updatedAt": "2026-07-29T00:00:00+00:00",
            }, {
                "id": "submodule-design",
                "type": "npm",
                "package": "@demo/submodule-design",
                "registry": "https://registry.npmjs.org/",
                "versionSpec": "latest",
                "resolvedVersion": "2.0.0",
                "tarball": "https://registry.npmjs.org/demo/-/submodule-design-2.0.0.tgz",
                "shasum": None,
                "integrity": "sha512-submodule",
                "mode": "repo",
                "targetPath": "repos/submodule-design",
                "skills": [{
                    "sourceDirectory": "skills/submodule-design",
                    "targetDirectory": "repos/submodule-design/skills/submodule-design",
                    "name": "submodule-design",
                    "fileHashes": {"SKILL.md": "submodule"},
                }],
                "importedAt": "2026-07-29T00:00:00+00:00",
                "updatedAt": "2026-07-29T00:00:00+00:00",
            }],
        }),
        encoding="utf-8",
    )

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
