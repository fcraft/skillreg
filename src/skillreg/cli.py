"""skillreg CLI entry point.

The CLI is intentionally a thin agent-friendly layer over the Python services:
it should work from any current directory as long as ``~/.skillreg/config.json``
points at the skill workspace.
"""

from __future__ import annotations

import threading
import time
import webbrowser
import os
import signal
import subprocess
from pathlib import Path
from typing import Optional, Sequence

import click
import uvicorn

from . import __version__
from .config import CONFIG_FILE, load_config, save_config

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787
DASHBOARD_PID_FILE = Path.home() / ".skillreg" / "dashboard.pid"
DASHBOARD_LOG_FILE = Path.home() / ".skillreg" / "dashboard.log"


def _format_csv(values: Sequence[str]) -> str:
    return ", ".join(values) if values else "(none)"


def _echo_workspace_summary(*, heading: str = "skillreg context") -> None:
    """Print the current workspace context after user-facing commands."""
    cfg = load_config()
    click.echo(heading)
    click.echo(f"  config file       : {CONFIG_FILE}")
    click.echo(f"  current workspace : {cfg.workspace_path or '(not configured)'}")
    click.echo(f"  sync targets      : {_format_csv(cfg.targets)}")


@click.group()
@click.version_option(version=__version__, package_name="skillreg")
def cli() -> None:
    """skillreg — skill registry control plane."""


@cli.command()
def config() -> None:
    """Print skillreg configuration status.

    Auto-creates ``~/.skillreg/config.json`` with the default empty structure
    on first run.
    """
    cfg = load_config()
    click.echo("skillreg config")
    click.echo(f"  config file : {CONFIG_FILE}")
    click.echo(f"  workspace   : {cfg.workspace_path or '(not configured)'}")
    click.echo(
        f"  targets     : "
        f"{', '.join(cfg.targets) if cfg.targets else '(none)'}"
    )
    click.echo(
        f"  agents      : "
        f"{', '.join(cfg.agents.keys()) if cfg.agents else '(none)'}"
    )


@cli.group()
def dashboard() -> None:
    """Manage the skillreg dashboard."""


@cli.group()
def workspace() -> None:
    """Manage skillreg workspaces."""


@cli.group()
def target() -> None:
    """Manage sync targets."""


@cli.group()
def sync() -> None:
    """Inspect and execute workspace sync."""


@cli.group()
def project() -> None:
    """Manage project sync groups."""


@cli.group()
def submodule() -> None:
    """Inspect workspace submodules."""


@workspace.command("create")
@click.argument("location", type=click.Path())
def create_workspace(location: str) -> None:
    """Create a new workspace at LOCATION.

    Initializes a git repo with skills/ and repos/ directories,
    writes .gitignore and README, and updates the config pointer.
    """
    from .services.importer import create_workspace as _create

    try:
        result = _create(location)
        click.echo(f"✓ Workspace created at {result['workspace_path']}")
        click.echo(f"  git init  : {'✓' if result['has_git'] else '✗'}")
        click.echo(f"  skills/   : {'✓' if result['has_skills_dir'] else '✗'}")
        click.echo(f"  repos/    : {'✓' if result['has_repos_dir'] else '✗'}")
        _echo_workspace_summary(heading="skillreg context after workspace create")
    except ValueError as e:
        click.echo(f"✗ {e}", err=True)
        raise SystemExit(1)


@workspace.command("current")
def current_workspace() -> None:
    """Print the current workspace pointer."""
    _echo_workspace_summary(heading="skillreg current workspace")


@workspace.command("switch")
@click.argument("location", type=click.Path(exists=True, file_okay=False))
def switch_workspace(location: str) -> None:
    """Switch to an existing workspace at LOCATION."""
    path = Path(location).expanduser().resolve()
    if not (path / "skills").is_dir():
        click.echo(f"✗ Workspace must contain a skills/ directory: {path}", err=True)
        raise SystemExit(1)
    cfg = load_config()
    cfg.workspace_path = str(path)
    save_config(cfg)
    click.echo(f"✓ Workspace switched to {path}")
    _echo_workspace_summary(heading="skillreg context after workspace switch")


@cli.command("register")
@click.argument("source_path", type=click.Path(exists=True, file_okay=False))
@click.option("--force", is_flag=True, default=False, help="Overwrite an existing skill.")
@click.option("--name", "rename_to", help="Register using a different skill name.")
def register_skill(source_path: str, force: bool, rename_to: str | None) -> None:
    """Register a local skill directory into the current workspace."""
    from .services.importer import import_skill

    try:
        result = import_skill(source_path, rename_to=rename_to, force=force)
    except (FileNotFoundError, ValueError) as e:
        click.echo(f"✗ Register failed: {e}", err=True)
        _echo_workspace_summary(heading="skillreg context after register failure")
        raise SystemExit(1)
    click.echo(f"✓ Registered skill: {result['name']}")
    click.echo(f"  source     : {Path(source_path).expanduser().resolve()}")
    click.echo(f"  skill path : {result['skillPath']}")
    click.echo(f"  files      : {result['filesCopied']}")
    click.echo(f"  commit     : {result.get('commit') or '(none)'}")
    _echo_workspace_summary(heading="skillreg context after register")


@cli.command("list")
def list_skills() -> None:
    """List skills in the current workspace."""
    from .services.skill_registry import get_all

    cfg = load_config()
    if not cfg.workspace_path:
        click.echo("✗ Workspace not configured", err=True)
        _echo_workspace_summary(heading="skillreg context after list failure")
        raise SystemExit(1)
    workspace_path = Path(cfg.workspace_path).expanduser().resolve()
    try:
        data = get_all(workspace_path)
    except Exception as e:
        click.echo(f"✗ List failed: {e}", err=True)
        raise SystemExit(1)
    skills = data.get("skills", [])
    if not skills:
        click.echo("(no skills found)")
    else:
        click.echo(f"{'NAME':<30} {'TYPE':<10} PATH")
        click.echo("-" * 72)
        for item in skills:
            click.echo(f"{item['name']:<30} {item['type']:<10} {item['path']}")
    click.echo(f"\nTotal: {len(skills)} skill(s)")
    _echo_workspace_summary(heading="skillreg context after list")


@cli.command("convert")
@click.argument("name")
def convert_skill(name: str) -> None:
    """Convert skills/NAME into repos/NAME-cli/skill/NAME."""
    from .services.importer import convert_skill as _convert

    try:
        result = _convert(name)
    except (FileNotFoundError, FileExistsError, ValueError) as e:
        click.echo(f"✗ Convert failed: {e}", err=True)
        _echo_workspace_summary(heading="skillreg context after convert failure")
        raise SystemExit(1)
    click.echo(f"✓ Converted skill: {result['name']}")
    click.echo(f"  repo path  : {result['repoPath']}")
    click.echo(f"  skill path : {result['skillPath']}")
    _echo_workspace_summary(heading="skillreg context after convert")


@target.command("list")
def list_targets() -> None:
    """List configured sync targets."""
    from .services.sync_manager import get_targets

    targets = get_targets()
    if not targets:
        click.echo("(no targets configured)")
    else:
        click.echo(f"{'NAME':<20} PATH")
        click.echo("-" * 72)
        for item in targets:
            click.echo(f"{item['name']:<20} {item['path']}")
    _echo_workspace_summary(heading="skillreg context after target list")


@target.command("add")
@click.argument("path", type=click.Path())
@click.option("--name", help="Display name for this target.")
def add_target(path: str, name: str | None) -> None:
    """Add PATH as a sync target."""
    from .services.sync_manager import add_target as _add

    resolved = str(Path(path).expanduser())
    try:
        result = _add(name or _target_display_label(resolved), resolved)
    except ValueError as e:
        click.echo(f"✗ Target add failed: {e}", err=True)
        raise SystemExit(1)
    click.echo(f"✓ Added target: {result['name']}")
    click.echo(f"  path : {result['path']}")
    _echo_workspace_summary(heading="skillreg context after target add")


@target.command("remove")
@click.argument("path")
def remove_target(path: str) -> None:
    """Remove a sync target by path."""
    from .services.sync_manager import remove_target as _remove

    resolved = str(Path(path).expanduser())
    try:
        _remove(resolved)
    except ValueError as e:
        click.echo(f"✗ Target remove failed: {e}", err=True)
        raise SystemExit(1)
    click.echo(f"✓ Removed target: {resolved}")
    _echo_workspace_summary(heading="skillreg context after target remove")


@target.command("rename")
@click.argument("old_path")
@click.argument("new_path")
def rename_target(old_path: str, new_path: str) -> None:
    """Replace an existing target path with NEW_PATH."""
    from .services.sync_manager import rename_target as _rename

    old_resolved = str(Path(old_path).expanduser())
    new_resolved = str(Path(new_path).expanduser())
    try:
        result = _rename(old_resolved, new_resolved)
    except ValueError as e:
        click.echo(f"✗ Target rename failed: {e}", err=True)
        raise SystemExit(1)
    click.echo("✓ Renamed target")
    click.echo(f"  path : {result['path']}")
    _echo_workspace_summary(heading="skillreg context after target rename")


@sync.command("status")
@click.option("--target", "target_path", help="Only inspect one target.")
@click.option("--skill", "skill_name", help="Only inspect one skill.")
@click.option("--include-projects", is_flag=True, default=False, help="Include project targets.")
def sync_status(target_path: str | None, skill_name: str | None, include_projects: bool) -> None:
    """Print per-skill sync status for configured targets."""
    from .services.sync_manager import get_sync_status

    rows = get_sync_status(
        target=target_path,
        include_projects=include_projects,
        skill=skill_name,
    )
    if not rows:
        click.echo("(no sync status rows)")
    else:
        click.echo(f"{'TARGET':<34} {'SKILL':<30} STATUS")
        click.echo("-" * 82)
        for row in rows:
            project_name = row.get("_project")
            target_label = row["target"]
            if project_name:
                target_label = f"{project_name}:{target_label}"
            click.echo(f"{target_label:<34} {row['name']:<30} {row['status']}")
    click.echo(f"\nTotal: {len(rows)} row(s)")
    _echo_workspace_summary(heading="skillreg context after sync status")


@sync.command("execute")
@click.option("--target", "target_path", help="Target directory to sync to.")
@click.option("--project", "project_id", help="Project id/name to sync to.")
@click.option("--skill", "skill_names", multiple=True, help="Skill name to sync; repeatable.")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without copying files.")
def sync_execute(
    target_path: str | None,
    project_id: str | None,
    skill_names: tuple[str, ...],
    dry_run: bool,
) -> None:
    """Execute sync for a target or project."""
    from .services import sync_manager

    skills = list(skill_names) or None
    results: list[dict] = []
    try:
        if project_id:
            project_entry = sync_manager.get_project(project_id)
            if not project_entry:
                raise ValueError(f"Project not found: {project_id}")
            for target_item in project_entry.get("targets", []):
                result = sync_manager.execute_sync(
                    target_item, dry_run=dry_run, skills=skills,
                )
                results.append({"target": target_item, **result})
            click.echo(f"✓ Synced project: {project_entry['name']}")
        else:
            if not target_path:
                raise ValueError("Missing --target or --project")
            result = sync_manager.execute_sync(
                target_path, dry_run=dry_run, skills=skills,
            )
            results.append({"target": target_path, **result})
            click.echo(f"✓ Sync {'previewed' if dry_run else 'executed'}")
    except (FileNotFoundError, ValueError) as e:
        click.echo(f"✗ Sync failed: {e}", err=True)
        _echo_workspace_summary(heading="skillreg context after sync failure")
        raise SystemExit(1)

    failed = False
    for result in results:
        click.echo(f"  target : {result['target']}")
        if result.get("stdout"):
            for line in str(result["stdout"]).splitlines():
                click.echo(f"    {line}")
        if result.get("stderr"):
            failed = True
            for line in str(result["stderr"]).splitlines():
                click.echo(f"    stderr: {line}", err=True)
        if not result.get("success", False):
            failed = True
    _echo_workspace_summary(heading="skillreg context after sync execute")
    if failed:
        raise SystemExit(1)


@cli.command("diff")
@click.argument("skill")
@click.option("--target", "target_path", required=True, help="Target directory to compare.")
def diff_skill(skill: str, target_path: str) -> None:
    """Compare a workspace skill against a target copy."""
    from .services.sync_manager import get_skill_diff

    try:
        rows = get_skill_diff(skill, target_path)
    except ValueError as e:
        click.echo(f"✗ Diff failed: {e}", err=True)
        raise SystemExit(1)
    if not rows:
        click.echo("(no files)")
    else:
        click.echo(f"{'STATUS':<12} PATH")
        click.echo("-" * 72)
        for row in rows:
            click.echo(f"{row['status']:<12} {row['path']}")
    click.echo(f"\nTotal: {len(rows)} file(s)")
    _echo_workspace_summary(heading="skillreg context after diff")


@project.command("list")
def list_projects() -> None:
    """List project sync groups."""
    from .services.sync_manager import list_projects as _list

    projects = _list()
    if not projects:
        click.echo("(no projects configured)")
    else:
        for item in projects:
            click.echo(f"{item['name']} ({item['id']})")
            for target_path in item.get("targets", []):
                click.echo(f"  - {target_path}")
    _echo_workspace_summary(heading="skillreg context after project list")


@project.command("create")
@click.option("--name", required=True, help="Project name.")
@click.option("--target", "targets", multiple=True, required=True, help="Target path; repeatable.")
def create_project(name: str, targets: tuple[str, ...]) -> None:
    """Create a project sync group."""
    from .services.sync_manager import create_project as _create

    result = _create(name, [str(Path(t).expanduser()) for t in targets])
    click.echo(f"✓ Created project: {result['name']}")
    click.echo(f"  id      : {result['id']}")
    click.echo(f"  targets : {len(result.get('targets', []))}")
    _echo_workspace_summary(heading="skillreg context after project create")


@project.command("info")
@click.argument("project_id")
def project_info(project_id: str) -> None:
    """Show a project sync group."""
    from .services.sync_manager import get_project

    result = get_project(project_id)
    if not result:
        click.echo(f"✗ Project not found: {project_id}", err=True)
        raise SystemExit(1)
    click.echo(f"name    : {result['name']}")
    click.echo(f"id      : {result['id']}")
    click.echo(f"created : {result.get('created_at', '(unknown)')}")
    click.echo("targets :")
    for target_path in result.get("targets", []):
        click.echo(f"  - {target_path}")


@project.command("add-target")
@click.argument("project_id")
@click.argument("path", type=click.Path())
def project_add_target(project_id: str, path: str) -> None:
    """Add a target to a project."""
    from .services.sync_manager import add_project_target

    try:
        result = add_project_target(project_id, str(Path(path).expanduser()))
    except ValueError as e:
        click.echo(f"✗ Project add-target failed: {e}", err=True)
        raise SystemExit(1)
    click.echo(f"✓ Added target to project: {result['name']}")


@project.command("remove-target")
@click.argument("project_id")
@click.argument("path", type=click.Path())
def project_remove_target(project_id: str, path: str) -> None:
    """Remove a target from a project."""
    from .services.sync_manager import remove_project_target

    try:
        result = remove_project_target(project_id, str(Path(path).expanduser()))
    except ValueError as e:
        click.echo(f"✗ Project remove-target failed: {e}", err=True)
        raise SystemExit(1)
    click.echo(f"✓ Removed target from project: {result['name']}")


@project.command("delete")
@click.argument("project_id")
def project_delete(project_id: str) -> None:
    """Delete a project sync group."""
    from .services.sync_manager import delete_project

    try:
        delete_project(project_id)
    except ValueError as e:
        click.echo(f"✗ Project delete failed: {e}", err=True)
        raise SystemExit(1)
    click.echo(f"✓ Deleted project: {project_id}")


@submodule.command("list")
def list_submodules() -> None:
    """List workspace submodules."""
    from .services.skill_registry import get_submodule_status, read_submodule_configs

    cfg = load_config()
    if not cfg.workspace_path:
        click.echo("✗ Workspace not configured", err=True)
        raise SystemExit(1)
    workspace_path = Path(cfg.workspace_path).expanduser().resolve()
    submodules = read_submodule_configs(workspace_path)
    if not submodules:
        click.echo("(no submodules found)")
    else:
        click.echo(f"{'PATH':<34} {'BRANCH':<14} STATE")
        click.echo("-" * 72)
        for item in submodules:
            status = get_submodule_status(
                workspace_path, item["path"], item["branch"],
            )
            click.echo(
                f"{item['path']:<34} {item['branch']:<14} "
                f"{status.get('syncState', 'unknown')}"
            )
    _echo_workspace_summary(heading="skillreg context after submodule list")


@dashboard.command("open")
@click.option("--host", default=DEFAULT_HOST, show_default=True, help="Bind host.")
@click.option("--port", default=DEFAULT_PORT, show_default=True, type=int, help="Bind port.")
@click.option(
    "--no-browser",
    is_flag=True,
    default=False,
    help="Do not open a browser; just start the server.",
)
def open_dashboard(host: str, port: int, no_browser: bool) -> None:
    """Start the FastAPI backend and open the dashboard in a browser."""
    url = f"http://{host}:{port}"
    if not no_browser:
        # Delay browser launch so uvicorn has a moment to bind the socket.
        threading.Thread(
            target=lambda: (time.sleep(1.0), webbrowser.open(url)),
            daemon=True,
        ).start()
    click.echo(f"skillreg backend starting at {url}")
    _echo_workspace_summary(heading="skillreg context for dashboard")
    click.echo("  press Ctrl+C to stop.")
    uvicorn.run(
        "skillreg.server:app",
        host=host,
        port=port,
        log_config=None,
    )


@dashboard.command("start")
@click.option("--host", default=DEFAULT_HOST, show_default=True, help="Bind host.")
@click.option("--port", default=DEFAULT_PORT, show_default=True, type=int, help="Bind port.")
def start_dashboard(host: str, port: int) -> None:
    """Start the dashboard backend in the background."""
    running_pid = _dashboard_running_pid()
    if running_pid:
        click.echo(f"✓ Dashboard already running (PID: {running_pid})")
        click.echo(f"  url : http://{host}:{port}")
        return

    DASHBOARD_PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    log = DASHBOARD_LOG_FILE.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [
            "python",
            "-m",
            "uvicorn",
            "skillreg.server:app",
            "--host",
            host,
            "--port",
            str(port),
        ],
        stdout=log,
        stderr=log,
        start_new_session=True,
    )
    log.close()
    DASHBOARD_PID_FILE.write_text(str(proc.pid), encoding="utf-8")
    click.echo(f"✓ Dashboard started (PID: {proc.pid})")
    click.echo(f"  url : http://{host}:{port}")
    click.echo(f"  log : {DASHBOARD_LOG_FILE}")
    _echo_workspace_summary(heading="skillreg context after dashboard start")


@dashboard.command("status")
def status_dashboard() -> None:
    """Print dashboard background process status."""
    running_pid = _dashboard_running_pid()
    if running_pid:
        click.echo(f"Dashboard running (PID: {running_pid})")
        click.echo(f"  pid file : {DASHBOARD_PID_FILE}")
        click.echo(f"  log file : {DASHBOARD_LOG_FILE}")
    else:
        click.echo("Dashboard not running")
    _echo_workspace_summary(heading="skillreg context after dashboard status")


@dashboard.command("stop")
def stop_dashboard() -> None:
    """Stop the background dashboard process."""
    running_pid = _dashboard_running_pid()
    if not running_pid:
        click.echo("Dashboard not running")
        return
    try:
        os.kill(running_pid, signal.SIGTERM)
    except OSError as e:
        click.echo(f"✗ Dashboard stop failed: {e}", err=True)
        raise SystemExit(1)
    DASHBOARD_PID_FILE.unlink(missing_ok=True)
    click.echo(f"✓ Dashboard stopped (PID: {running_pid})")
    _echo_workspace_summary(heading="skillreg context after dashboard stop")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point for the ``skillreg`` console script."""
    cli(args=list(argv) if argv is not None else None, standalone_mode=True)
    return 0


def _target_display_label(path: str) -> str:
    path_obj = Path(path).expanduser()
    if path_obj.name == "skills" and path_obj.parent.name.startswith("."):
        return path_obj.parent.name[1:]
    return path_obj.name or path


def _dashboard_running_pid() -> int | None:
    if not DASHBOARD_PID_FILE.exists():
        return None
    try:
        pid = int(DASHBOARD_PID_FILE.read_text(encoding="utf-8").strip())
        os.kill(pid, 0)
        return pid
    except (ValueError, OSError):
        DASHBOARD_PID_FILE.unlink(missing_ok=True)
        return None


if __name__ == "__main__":
    main()
