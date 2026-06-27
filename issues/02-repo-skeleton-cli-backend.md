# skillreg greenfield 仓骨架 + CLI 入口 + Python 后端框架

## What to build

在 `~/Code/project_kex/skillreg`（已 `git init` 连 `fcraft/skillreg`）建立 monorepo 骨架，使 skillreg 作为一个 Python CLI 可安装、可启动，dashboard 能打开（空占位即可）。

骨架包含：
- 根 `pyproject.toml`：skillreg Python 包，`uv tool install -e .` 可装，入口命令 `skillreg`
- `server/`：FastAPI 后端，`/api/health` 端点返回当前配置的 workspace 路径
- `dashboard/`：占位目录（前端迁入在后续 issue）
- `specs/`：已含 `skillreg-v2.md` PRD
- `skillreg-cli/`、`self-skill/`、`ui-framework/`：三个 submodule 占位（先建空目录或 placeholder，正式 submodule 接入在后续 issue）
- `~/.skillreg/config.json` 配置读写：含 workspace 指针字段（`workspace_path`）、targets、agent 约定；不存在则创建空配置

CLI 命令（最小集）：
- `skillreg config`：输出配置状态（配置文件路径、workspace 指针、targets）
- `skillreg dashboard open`：启动 FastAPI 后端 + 浏览器打开（dashboard 占位页即可）

**配置归属**遵循 PRD 2.3：workspace 只放 skills/+repos/；targets/agent 约定/workspace 指针全在 `~/.skillreg/config.json`。

## Acceptance criteria

- [ ] `uv tool install -e .` 成功，`skillreg` 命令可用
- [ ] `skillreg config` 输出配置状态，首次运行自动创建 `~/.skillreg/config.json`
- [ ] `~/.skillreg/config.json` 含 workspace 指针、targets、agent 约定字段
- [ ] `skillreg dashboard open` 启动 FastAPI 后端并打开浏览器
- [ ] `/api/health` 返回当前配置的 workspace 路径（未配置则提示）
- [ ] monorepo 骨架目录结构符合 PRD 2.1
- [ ] 首次 commit 推送到 `fcraft/skillreg`，提交身份 `HJH201314 <fcraft@qq.com>`

## Blocked by

None - can start immediately（与 #1 契约冻结并行）
