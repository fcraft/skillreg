# skillreg

`skillreg` 是一个面向 AI Agent Skill 的本地管理中控。它负责把用户或
agent 在任意项目里写好的 `SKILL.md` 注册到一个独立的 skill workspace，
再同步到 Claude、Codex、CodeBuddy、`~/.agents/skills` 等 agent 目标目录。

[![CI](https://github.com/fcraft/skillreg/actions/workflows/ci.yml/badge.svg)](https://github.com/fcraft/skillreg/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![License MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## 核心心智

用户不需要关心“产品仓”“workspace 仓”这些实现细节：

- 本地任意项目里只要有一个包含 `SKILL.md` 的目录，就可以注册为 skill。
- `skillreg` 使用 `~/.skillreg/config.json` 记录当前正在管理的 workspace。
- 注册后的 skill 进入 workspace 的 `skills/` 或 `repos/`。
- 同步目标由 workspace 配置管理，可以分发到不同 agent 的 skill 目录。
- CLI 会在关键命令后输出 `current workspace`，方便 agent 执行命令后立刻知道当前操作对象。

## 当前能力

- 创建 workspace，并写入 `~/.skillreg/config.json`
- 导入本地目录、zip、git 仓库中的 skill
- 浏览 workspace 中的 skills、文件树、依赖关系、git 日志、submodule 状态
- 在 dashboard 中切换当前 workspace
- 管理 sync targets，并把 skill 同步到 agent 目录
- 查看 target 中已安装 skill、差异、目标文件
- 提供 GitHub tag 发版流程，校验 `pyproject.toml`、`__version__` 和 tag 一致

## 快速开始

```bash
# 1. 安装
uv tool install skillreg

# 2. 创建一个新的 workspace
skillreg workspace create ~/my-skills

# 3. 打开 dashboard
skillreg dashboard open
```

默认会打开：

```text
http://127.0.0.1:8787
```

如果已经有 workspace，可以在 dashboard header 中切换到那个目录。workspace
至少需要包含一个 `skills/` 目录。

## 常用命令

```bash
skillreg config
skillreg workspace create <path>
skillreg dashboard open
skillreg dashboard open --no-browser
```

`skillreg config` 会输出当前配置：

```text
skillreg config
  config file : /Users/me/.skillreg/config.json
  workspace   : /Users/me/my-skills
  targets     : /Users/me/.agents/skills
  agents      : (none)
```

创建 workspace 或打开 dashboard 时，CLI 也会输出当前 `skillreg context`，让
agent 能在执行命令后快速判断下一步。

## Workspace 模型

```text
<workspace>/
├── skills/                  # 单个目录型 skills
├── repos/                   # repo / CLI 型 skills
└── .skillreg/builtin/       # 自动注入的 skillreg-skill 保留区
```

本地配置统一放在：

```text
~/.skillreg/config.json
```

核心字段：

- `workspace_path`: 当前正在管理的 workspace
- `targets`: sync 目标目录列表
- `agents`: agent 约定配置

## Dashboard

Dashboard 当前主页面包括：

- `Skill 列表`
- `Sync 工具`
- `项目组`
- `仓库状态`
- `依赖关系图`
- `提交记录`
- `组件实验室`

## 开发

```bash
git clone https://github.com/fcraft/skillreg.git
cd skillreg
uv venv
uv pip install -e ".[dev]"
uv pip install ruff build
python scripts/check_version.py
python -m pytest -q
ruff check src/ tests/ scripts/
```

本地启动：

```bash
skillreg dashboard open --no-browser
```

或：

```bash
python -m uvicorn skillreg.server:app --host 127.0.0.1 --port 8787
```

## 发版

`pyproject.toml` 是人工维护的版本号源头。发版 PR 需要同步：

- `pyproject.toml` 的 `[project].version`
- `src/skillreg/__init__.py` 的 `__version__`

合入后推送匹配 tag：

```bash
git tag v0.2.0
git push origin v0.2.0
```

GitHub Release workflow 会校验版本/tag 一致、运行测试、构建 wheel/sdist，
并创建 GitHub Release。详细流程见 [docs/release-process.md](docs/release-process.md)。

## License

MIT
