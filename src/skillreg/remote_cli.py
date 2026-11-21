"""CLI commands for SSH connections and persistent sync runs"""

from __future__ import annotations

import json
from pathlib import Path
from functools import wraps

import click

from .services import ssh_connections, sync_inventory, sync_manager, sync_runs, sync_targets


def output(value):
    click.echo(json.dumps(value, ensure_ascii=False, indent=2))


def errors(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except (ValueError, OSError) as exc:
            raise click.ClickException(str(exc)) from exc

    return wrapped


def execute(target_ids, skills, preview_id, force, dry_run):
    if preview_id and (target_ids or skills):
        raise ValueError("--preview-id cannot be combined with new targets or skills")
    if not preview_id:
        planned = sync_runs.preview(list(target_ids), list(skills) or None)
        preview_id = planned["id"]
        if dry_run:
            output(planned)
            return
    elif dry_run:
        raise ValueError("Use sync preview to create a dry run")
    run = sync_runs.create_run(preview_id, force=force, background=False)
    output(run)
    if run["state"] != "succeeded":
        raise click.exceptions.Exit(1)


def register(cli, target, sync):
    @target.command("inventory")
    @click.argument("identifier")
    @errors
    def inventory(identifier):
        """探测已保存目标中的 Skill，不递归计算文件摘要"""
        output(sync_inventory.inspect_target(identifier))

    @target.command("read-skill")
    @click.argument("identifier")
    @click.argument("name")
    @errors
    def read_skill(identifier, name):
        """读取目标中某个 Skill 的 SKILL.md"""
        output(sync_inventory.read_skill(identifier, name))

    @cli.group("connection")
    def connection():
        """管理 SSH 连接"""

    @connection.command("list")
    @errors
    def connection_list():
        """列出连接和最近检查结果"""
        output(ssh_connections.list_connections())

    @connection.command("add")
    @click.option("--name", required=True, help="连接显示名称")
    @click.option("--host", required=True, help="OpenSSH Host 别名或主机地址")
    @click.option("--user", help="SSH 用户，省略时使用 SSH 配置")
    @click.option("--port", type=click.IntRange(1, 65535), help="SSH 端口")
    @click.option("--identity-file", help="本机私钥路径，不保存私钥内容")
    @errors
    def connection_add(name, host, user, port, identity_file):
        """保存 SSH 连接配置"""
        output(ssh_connections.save_connection(name, host, user, port, identity_file))

    @connection.command("check")
    @click.argument("identifier")
    @errors
    def connection_check(identifier):
        """检查连接、主机信任和远端 Python 能力"""
        result = ssh_connections.check_connection(identifier)
        output(result)
        if result["status"] != "online":
            raise click.exceptions.Exit(1)

    @connection.command("remove")
    @click.argument("identifier")
    @errors
    def connection_remove(identifier):
        """移除没有关联目标的连接"""
        ssh_connections.remove_connection(identifier)
        output({"removed": identifier})

    @target.command("discover")
    @click.option("--connection", help="SSH 连接 ID 或名称；省略时探测本机内置 Agent 目录")
    @click.option("--root", help="项目根目录；省略时探测全局 ~/ Agent 目录")
    @click.option("--all", "include_all", is_flag=True, help="包含本机未检测到的内置 Agent 预设（仅本机全局探测）")
    @errors
    def discover(connection, root, include_all):
        """发现本机或远端 Agent Skill 目录"""
        if connection:
            output(ssh_connections.discover(connection, root))
            return
        if root:
            resolved = str(Path(root).expanduser().resolve())
            output({"root": resolved, "agent_dirs": sync_manager.discover_agent_dirs(root)})
            return
        output(sync_manager.list_builtin_agents(include_undetected=include_all))

    @target.command("label")
    @click.argument("identifier")
    @click.argument("name")
    @errors
    def label(identifier, name):
        """更新显示名称，保持目标 ID 和路径不变"""
        output(sync_targets.update_target(identifier, name=name))

    @sync.command("preview")
    @click.option(
        "--target-id",
        "target_ids",
        multiple=True,
        required=True,
        help="目标 ID，可重复",
    )
    @click.option(
        "--skill", "skills", multiple=True, help="选择 Skill，可重复；省略使用目标筛选"
    )
    @errors
    def preview(target_ids, skills):
        """预览差异并返回有效期 15 分钟的预览 ID"""
        output(sync_runs.preview(list(target_ids), list(skills) or None))

    @sync.command("run")
    @click.argument("identifier")
    @errors
    def run(identifier):
        """查询同步执行结果"""
        output(sync_runs.get_run(identifier))

    @sync.command("history")
    @click.option(
        "--limit", type=click.IntRange(1, 200), default=50, help="最多返回的执行记录数"
    )
    @errors
    def history(limit):
        """查看同步执行历史"""
        output(sync_runs.history(limit))

    @sync.command("retry")
    @click.argument("identifier")
    @errors
    def retry(identifier):
        """为失败目标重新生成预览，确认后用 execute --preview-id 执行"""
        output(sync_runs.retry_preview(identifier))

    @sync.command("cancel")
    @click.argument("identifier")
    @errors
    def cancel(identifier):
        """请求取消；当前 Skill 完成后停止后续安装"""
        output(sync_runs.cancel_run(identifier))
