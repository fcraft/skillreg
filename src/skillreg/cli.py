"""skillreg CLI entry point.

Minimal command set for M1 (issue #02):

- ``skillreg config``           — print config status (auto-creates config).
- ``skillreg dashboard open``   — start the FastAPI backend + open a browser.

Built with `click`. The entry point ``skillreg = "skillreg.cli:main"`` is
declared in ``pyproject.toml``.
"""

from __future__ import annotations

import threading
import time
import webbrowser
from typing import Optional, Sequence

import click
import uvicorn

from . import __version__
from .config import CONFIG_FILE, load_config

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787


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


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point for the ``skillreg`` console script."""
    cli(args=list(argv) if argv is not None else None, standalone_mode=True)
    return 0


if __name__ == "__main__":
    main()
