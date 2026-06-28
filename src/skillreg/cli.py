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
CONTEXT_SETTINGS = {
    "help_option_names": ["-h", "--help"],
}


class ChineseHelpMixin:
    @staticmethod
    def _show_help(ctx: click.Context, _param: click.Parameter, value: bool) -> None:
        if value and not ctx.resilient_parsing:
            click.echo(ctx.get_help(), color=ctx.color)
            ctx.exit()

    def get_help_option(self, ctx: click.Context) -> click.Option | None:
        help_options = self.get_help_option_names(ctx)
        if not help_options or not self.add_help_option:
            return None
        if self._help_option is None:
            self._help_option = click.Option(
                help_options,
                is_flag=True,
                expose_value=False,
                is_eager=True,
                help="显示帮助信息并退出。",
                callback=self._show_help,
            )
        return self._help_option


class SkillregCommand(ChineseHelpMixin, click.Command):
    """Click command that supports both -h and --help."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("context_settings", CONTEXT_SETTINGS)
        super().__init__(*args, **kwargs)


class SkillregGroup(ChineseHelpMixin, click.Group):
    """Click group that creates skillreg commands by default."""

    command_class = SkillregCommand

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("context_settings", CONTEXT_SETTINGS)
        super().__init__(*args, **kwargs)


SkillregGroup.group_class = SkillregGroup


def _format_csv(values: Sequence[str]) -> str:
    return ", ".join(values) if values else "(none)"


def _echo_workspace_summary(*, heading: str = "skillreg 上下文") -> None:
    """Print the current workspace context after user-facing commands."""
    cfg = load_config()
    click.echo(heading)
    click.echo(f"  配置文件       : {CONFIG_FILE}")
    click.echo(f"  当前 workspace : {cfg.workspace_path or '(未配置)'}")
    click.echo(f"  同步目标       : {_format_csv(cfg.targets)}")


@click.group(cls=SkillregGroup)
@click.version_option(version=__version__, package_name="skillreg", help="显示版本信息并退出。")
def cli() -> None:
    """skillreg — 本地 AI Agent Skill 管理工具。"""


@cli.command()
def config() -> None:
    """查看 skillreg 配置状态。

    首次运行会自动创建默认的 ``~/.skillreg/config.json``。
    """
    cfg = load_config()
    click.echo("skillreg 配置")
    click.echo(f"  配置文件  : {CONFIG_FILE}")
    click.echo(f"  workspace : {cfg.workspace_path or '(未配置)'}")
    click.echo(
        f"  同步目标  : "
        f"{', '.join(cfg.targets) if cfg.targets else '(none)'}"
    )
    click.echo(
        f"  agents     : "
        f"{', '.join(cfg.agents.keys()) if cfg.agents else '(none)'}"
    )


@cli.group()
def dashboard() -> None:
    """管理 skillreg dashboard。"""


@cli.group()
def workspace() -> None:
    """管理 skillreg workspace。"""


@cli.group()
def target() -> None:
    """管理同步目标。"""


@cli.group()
def sync() -> None:
    """查看并执行 workspace 同步。"""


@cli.group()
def project() -> None:
    """管理项目同步组。"""


@cli.group()
def submodule() -> None:
    """查看 workspace 子模块。"""


@workspace.command("create")
@click.argument("location", type=click.Path())
def create_workspace(location: str) -> None:
    """在 LOCATION 创建新的 workspace。

    会初始化 git 仓库，创建 skills/ 与 repos/ 目录，并更新配置指针。
    """
    from .services.importer import create_workspace as _create

    try:
        result = _create(location)
        click.echo(f"✓ 已创建 workspace: {result['workspace_path']}")
        click.echo(f"  git init  : {'✓' if result['has_git'] else '✗'}")
        click.echo(f"  skills/   : {'✓' if result['has_skills_dir'] else '✗'}")
        click.echo(f"  repos/    : {'✓' if result['has_repos_dir'] else '✗'}")
        _echo_workspace_summary(heading="创建 workspace 后的 skillreg 上下文")
    except ValueError as e:
        click.echo(f"✗ {e}", err=True)
        raise SystemExit(1)


@workspace.command("current")
def current_workspace() -> None:
    """查看当前 workspace 指针。"""
    _echo_workspace_summary(heading="当前 skillreg workspace")


@workspace.command("switch")
@click.argument("location", type=click.Path(exists=True, file_okay=False))
def switch_workspace(location: str) -> None:
    """切换到已有 workspace。"""
    path = Path(location).expanduser().resolve()
    if not (path / "skills").is_dir():
        click.echo(f"✗ workspace 必须包含 skills/ 目录: {path}", err=True)
        raise SystemExit(1)
    cfg = load_config()
    cfg.workspace_path = str(path)
    save_config(cfg)
    click.echo(f"✓ 已切换 workspace: {path}")
    _echo_workspace_summary(heading="切换 workspace 后的 skillreg 上下文")


@cli.command("register")
@click.argument("source_path", type=click.Path(exists=True, file_okay=False))
@click.option("--force", is_flag=True, default=False, help="覆盖同名 skill。")
@click.option("--name", "rename_to", help="使用指定名称注册 skill。")
def register_skill(source_path: str, force: bool, rename_to: str | None) -> None:
    """把本地 skill 目录注册到当前 workspace。"""
    from .services.importer import import_skill

    try:
        result = import_skill(source_path, rename_to=rename_to, force=force)
    except (FileNotFoundError, ValueError) as e:
        click.echo(f"✗ 注册失败: {e}", err=True)
        _echo_workspace_summary(heading="注册失败时的 skillreg 上下文")
        raise SystemExit(1)
    click.echo(f"✓ 已注册 skill: {result['name']}")
    click.echo(f"  来源       : {Path(source_path).expanduser().resolve()}")
    click.echo(f"  skill 路径 : {result['skillPath']}")
    click.echo(f"  文件数     : {result['filesCopied']}")
    click.echo(f"  commit     : {result.get('commit') or '(none)'}")
    _echo_workspace_summary(heading="注册后的 skillreg 上下文")


@cli.command("list")
def list_skills() -> None:
    """列出当前 workspace 中的 skills。"""
    from .services.skill_registry import get_all

    cfg = load_config()
    if not cfg.workspace_path:
        click.echo("✗ workspace 未配置", err=True)
        _echo_workspace_summary(heading="列出失败时的 skillreg 上下文")
        raise SystemExit(1)
    workspace_path = Path(cfg.workspace_path).expanduser().resolve()
    try:
        data = get_all(workspace_path)
    except Exception as e:
        click.echo(f"✗ 列出失败: {e}", err=True)
        raise SystemExit(1)
    skills = data.get("skills", [])
    if not skills:
        click.echo("(no skills found)")
    else:
        click.echo(f"{'名称':<30} {'类型':<10} 路径")
        click.echo("-" * 72)
        for item in skills:
            click.echo(f"{item['name']:<30} {item['type']:<10} {item['path']}")
    click.echo(f"\n总计: {len(skills)} 个 skill")
    _echo_workspace_summary(heading="列出后的 skillreg 上下文")


@cli.command("convert")
@click.argument("name")
def convert_skill(name: str) -> None:
    """把 skills/NAME 转换为 repos/NAME-cli/skill/NAME。"""
    from .services.importer import convert_skill as _convert

    try:
        result = _convert(name)
    except (FileNotFoundError, FileExistsError, ValueError) as e:
        click.echo(f"✗ 转换失败: {e}", err=True)
        _echo_workspace_summary(heading="转换失败时的 skillreg 上下文")
        raise SystemExit(1)
    click.echo(f"✓ 已转换 skill: {result['name']}")
    click.echo(f"  repo 路径  : {result['repoPath']}")
    click.echo(f"  skill 路径 : {result['skillPath']}")
    _echo_workspace_summary(heading="转换后的 skillreg 上下文")


@target.command("list")
def list_targets() -> None:
    """列出已配置的同步目标。"""
    from .services.sync_manager import get_targets

    targets = get_targets()
    if not targets:
        click.echo("(no targets configured)")
    else:
        click.echo(f"{'名称':<20} 路径")
        click.echo("-" * 72)
        for item in targets:
            click.echo(f"{item['name']:<20} {item['path']}")
    _echo_workspace_summary(heading="列出同步目标后的 skillreg 上下文")


@target.command("add")
@click.argument("path", type=click.Path())
@click.option("--name", help="同步目标的显示名称。")
def add_target(path: str, name: str | None) -> None:
    """添加同步目标 PATH。"""
    from .services.sync_manager import add_target as _add

    resolved = str(Path(path).expanduser())
    try:
        result = _add(name or _target_display_label(resolved), resolved)
    except ValueError as e:
        click.echo(f"✗ 添加同步目标失败: {e}", err=True)
        raise SystemExit(1)
    click.echo(f"✓ 已添加同步目标: {result['name']}")
    click.echo(f"  路径 : {result['path']}")
    _echo_workspace_summary(heading="添加同步目标后的 skillreg 上下文")


@target.command("remove")
@click.argument("path")
def remove_target(path: str) -> None:
    """按路径移除同步目标。"""
    from .services.sync_manager import remove_target as _remove

    resolved = str(Path(path).expanduser())
    try:
        _remove(resolved)
    except ValueError as e:
        click.echo(f"✗ 移除同步目标失败: {e}", err=True)
        raise SystemExit(1)
    click.echo(f"✓ 已移除同步目标: {resolved}")
    _echo_workspace_summary(heading="移除同步目标后的 skillreg 上下文")


@target.command("rename")
@click.argument("old_path")
@click.argument("new_path")
def rename_target(old_path: str, new_path: str) -> None:
    """把已有同步目标路径替换为 NEW_PATH。"""
    from .services.sync_manager import rename_target as _rename

    old_resolved = str(Path(old_path).expanduser())
    new_resolved = str(Path(new_path).expanduser())
    try:
        result = _rename(old_resolved, new_resolved)
    except ValueError as e:
        click.echo(f"✗ 重命名同步目标失败: {e}", err=True)
        raise SystemExit(1)
    click.echo("✓ 已重命名同步目标")
    click.echo(f"  路径 : {result['path']}")
    _echo_workspace_summary(heading="重命名同步目标后的 skillreg 上下文")


@sync.command("status")
@click.option("--target", "target_path", help="只查看一个同步目标。")
@click.option("--skill", "skill_name", help="只查看一个 skill。")
@click.option("--include-projects", is_flag=True, default=False, help="包含项目组同步目标。")
def sync_status(target_path: str | None, skill_name: str | None, include_projects: bool) -> None:
    """查看各同步目标中的 skill 同步状态。"""
    from .services.sync_manager import get_sync_status

    rows = get_sync_status(
        target=target_path,
        include_projects=include_projects,
        skill=skill_name,
    )
    if not rows:
        click.echo("(no sync status rows)")
    else:
        click.echo(f"{'同步目标':<34} {'SKILL':<30} 状态")
        click.echo("-" * 82)
        for row in rows:
            project_name = row.get("_project")
            target_label = row["target"]
            if project_name:
                target_label = f"{project_name}:{target_label}"
            click.echo(f"{target_label:<34} {row['name']:<30} {row['status']}")
    click.echo(f"\n总计: {len(rows)} 条状态")
    _echo_workspace_summary(heading="查看同步状态后的 skillreg 上下文")


@sync.command("execute")
@click.option("--target", "target_path", help="要同步到的目标目录。")
@click.option("--project", "project_id", help="要同步的项目组 ID 或名称。")
@click.option("--skill", "skill_names", multiple=True, help="要同步的 skill 名称，可重复传入。")
@click.option("--dry-run", is_flag=True, default=False, help="只预览，不复制文件。")
def sync_execute(
    target_path: str | None,
    project_id: str | None,
    skill_names: tuple[str, ...],
    dry_run: bool,
) -> None:
    """执行同步到目标目录或项目组。"""
    from .services import sync_manager

    skills = list(skill_names) or None
    results: list[dict] = []
    try:
        if project_id:
            project_entry = sync_manager.get_project(project_id)
            if not project_entry:
                raise ValueError(f"项目组不存在: {project_id}")
            for target_item in project_entry.get("targets", []):
                result = sync_manager.execute_sync(
                    target_item, dry_run=dry_run, skills=skills,
                )
                results.append({"target": target_item, **result})
            click.echo(f"✓ 已同步项目组: {project_entry['name']}")
        else:
            if not target_path:
                raise ValueError("缺少 --target 或 --project")
            result = sync_manager.execute_sync(
                target_path, dry_run=dry_run, skills=skills,
            )
            results.append({"target": target_path, **result})
            click.echo(f"✓ 同步{'预览' if dry_run else '完成'}")
    except (FileNotFoundError, ValueError) as e:
        click.echo(f"✗ 同步失败: {e}", err=True)
        _echo_workspace_summary(heading="同步失败时的 skillreg 上下文")
        raise SystemExit(1)

    failed = False
    for result in results:
        click.echo(f"  同步目标 : {result['target']}")
        if result.get("stdout"):
            for line in str(result["stdout"]).splitlines():
                click.echo(f"    {line}")
        if result.get("stderr"):
            failed = True
            for line in str(result["stderr"]).splitlines():
                click.echo(f"    错误: {line}", err=True)
        if not result.get("success", False):
            failed = True
    _echo_workspace_summary(heading="执行同步后的 skillreg 上下文")
    if failed:
        raise SystemExit(1)


@cli.command("diff")
@click.argument("skill")
@click.option("--target", "target_path", required=True, help="要比较的目标目录。")
def diff_skill(skill: str, target_path: str) -> None:
    """比较 workspace skill 与目标目录中的副本。"""
    from .services.sync_manager import get_skill_diff

    try:
        rows = get_skill_diff(skill, target_path)
    except ValueError as e:
        click.echo(f"✗ 比较失败: {e}", err=True)
        raise SystemExit(1)
    if not rows:
        click.echo("(no files)")
    else:
        click.echo(f"{'状态':<12} 路径")
        click.echo("-" * 72)
        for row in rows:
            click.echo(f"{row['status']:<12} {row['path']}")
    click.echo(f"\n总计: {len(rows)} 个文件")
    _echo_workspace_summary(heading="比较后的 skillreg 上下文")


@project.command("list")
def list_projects() -> None:
    """列出项目同步组。"""
    from .services.sync_manager import list_projects as _list

    projects = _list()
    if not projects:
        click.echo("(no projects configured)")
    else:
        for item in projects:
            click.echo(f"{item['name']} ({item['id']})")
            for target_path in item.get("targets", []):
                click.echo(f"  - {target_path}")
    _echo_workspace_summary(heading="列出项目组后的 skillreg 上下文")


@project.command("create")
@click.option("--name", required=True, help="项目组名称。")
@click.option("--target", "targets", multiple=True, required=True, help="同步目标路径，可重复传入。")
def create_project(name: str, targets: tuple[str, ...]) -> None:
    """创建项目同步组。"""
    from .services.sync_manager import create_project as _create

    result = _create(name, [str(Path(t).expanduser()) for t in targets])
    click.echo(f"✓ 已创建项目组: {result['name']}")
    click.echo(f"  id      : {result['id']}")
    click.echo(f"  同步目标数 : {len(result.get('targets', []))}")
    _echo_workspace_summary(heading="创建项目组后的 skillreg 上下文")


@project.command("info")
@click.argument("project_id")
def project_info(project_id: str) -> None:
    """查看项目同步组详情。"""
    from .services.sync_manager import get_project

    result = get_project(project_id)
    if not result:
        click.echo(f"✗ 项目组不存在: {project_id}", err=True)
        raise SystemExit(1)
    click.echo(f"name    : {result['name']}")
    click.echo(f"id      : {result['id']}")
    click.echo(f"created : {result.get('created_at', '(unknown)')}")
    click.echo("同步目标 :")
    for target_path in result.get("targets", []):
        click.echo(f"  - {target_path}")


@project.command("add-target")
@click.argument("project_id")
@click.argument("path", type=click.Path())
def project_add_target(project_id: str, path: str) -> None:
    """为项目同步组添加目标。"""
    from .services.sync_manager import add_project_target

    try:
        result = add_project_target(project_id, str(Path(path).expanduser()))
    except ValueError as e:
        click.echo(f"✗ 添加项目组目标失败: {e}", err=True)
        raise SystemExit(1)
    click.echo(f"✓ 已添加目标到项目组: {result['name']}")


@project.command("remove-target")
@click.argument("project_id")
@click.argument("path", type=click.Path())
def project_remove_target(project_id: str, path: str) -> None:
    """从项目同步组移除目标。"""
    from .services.sync_manager import remove_project_target

    try:
        result = remove_project_target(project_id, str(Path(path).expanduser()))
    except ValueError as e:
        click.echo(f"✗ 移除项目组目标失败: {e}", err=True)
        raise SystemExit(1)
    click.echo(f"✓ 已从项目组移除目标: {result['name']}")


@project.command("delete")
@click.argument("project_id")
def project_delete(project_id: str) -> None:
    """删除项目同步组。"""
    from .services.sync_manager import delete_project

    try:
        delete_project(project_id)
    except ValueError as e:
        click.echo(f"✗ 删除项目组失败: {e}", err=True)
        raise SystemExit(1)
    click.echo(f"✓ 已删除项目组: {project_id}")


@submodule.command("list")
def list_submodules() -> None:
    """列出 workspace 子模块。"""
    from .services.skill_registry import get_submodule_status, read_submodule_configs

    cfg = load_config()
    if not cfg.workspace_path:
        click.echo("✗ workspace 未配置", err=True)
        raise SystemExit(1)
    workspace_path = Path(cfg.workspace_path).expanduser().resolve()
    submodules = read_submodule_configs(workspace_path)
    if not submodules:
        click.echo("(no submodules found)")
    else:
        click.echo(f"{'路径':<34} {'分支':<14} 状态")
        click.echo("-" * 72)
        for item in submodules:
            status = get_submodule_status(
                workspace_path, item["path"], item["branch"],
            )
            click.echo(
                f"{item['path']:<34} {item['branch']:<14} "
                f"{status.get('syncState', 'unknown')}"
            )
    _echo_workspace_summary(heading="列出子模块后的 skillreg 上下文")


@dashboard.command("open")
@click.option("--host", default=DEFAULT_HOST, show_default=True, help="绑定 host。")
@click.option("--port", default=DEFAULT_PORT, show_default=True, type=int, help="绑定端口。")
@click.option(
    "--no-browser",
    is_flag=True,
    default=False,
    help="只启动服务，不打开浏览器。",
)
def open_dashboard(host: str, port: int, no_browser: bool) -> None:
    """启动 FastAPI 后端并打开 dashboard。"""
    url = f"http://{host}:{port}"
    if not no_browser:
        # Delay browser launch so uvicorn has a moment to bind the socket.
        threading.Thread(
            target=lambda: (time.sleep(1.0), webbrowser.open(url)),
            daemon=True,
        ).start()
    click.echo(f"skillreg 后端启动中: {url}")
    _echo_workspace_summary(heading="dashboard 启动时的 skillreg 上下文")
    click.echo("  按 Ctrl+C 停止。")
    uvicorn.run(
        "skillreg.server:app",
        host=host,
        port=port,
        log_config=None,
    )


@dashboard.command("start")
@click.option("--host", default=DEFAULT_HOST, show_default=True, help="绑定 host。")
@click.option("--port", default=DEFAULT_PORT, show_default=True, type=int, help="绑定端口。")
def start_dashboard(host: str, port: int) -> None:
    """在后台启动 dashboard 后端。"""
    running_pid = _dashboard_running_pid()
    if running_pid:
        click.echo(f"✓ Dashboard 已在运行 (PID: {running_pid})")
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
    click.echo(f"✓ Dashboard 已启动 (PID: {proc.pid})")
    click.echo(f"  url : http://{host}:{port}")
    click.echo(f"  日志 : {DASHBOARD_LOG_FILE}")
    _echo_workspace_summary(heading="dashboard 启动后的 skillreg 上下文")


@dashboard.command("status")
def status_dashboard() -> None:
    """查看 dashboard 后台进程状态。"""
    running_pid = _dashboard_running_pid()
    if running_pid:
        click.echo(f"Dashboard 运行中 (PID: {running_pid})")
        click.echo(f"  PID 文件 : {DASHBOARD_PID_FILE}")
        click.echo(f"  日志文件 : {DASHBOARD_LOG_FILE}")
    else:
        click.echo("Dashboard 未运行")
    _echo_workspace_summary(heading="查看 dashboard 状态后的 skillreg 上下文")


@dashboard.command("stop")
def stop_dashboard() -> None:
    """停止后台 dashboard 进程。"""
    running_pid = _dashboard_running_pid()
    if not running_pid:
        click.echo("Dashboard 未运行")
        return
    try:
        os.kill(running_pid, signal.SIGTERM)
    except OSError as e:
        click.echo(f"✗ 停止 Dashboard 失败: {e}", err=True)
        raise SystemExit(1)
    DASHBOARD_PID_FILE.unlink(missing_ok=True)
    click.echo(f"✓ Dashboard 已停止 (PID: {running_pid})")
    _echo_workspace_summary(heading="dashboard 停止后的 skillreg 上下文")


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
