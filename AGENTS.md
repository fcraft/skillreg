# AGENTS.md

## 项目定位

`skillreg` 是本地 AI Agent Skill 管理工具，发布为 PyPI 包 `skillreg`。

当前项目由三部分组成：

- **CLI**：`skillreg` 命令，面向 agent 和开发者的自动化入口。
- **FastAPI backend**：Dashboard 和兼容接口的服务层。
- **Dashboard**：面向人类用户的图形管理入口。

管理对象是用户本地的 skill workspace。workspace 通常只包含：

- `skills/`：直接注册进 workspace 的 skills。
- `repos/`：转换为子仓/CLI 骨架后的 skills。

不要再把本仓描述成依赖 `agent-hub` 运行，也不要引用旧的
`skillreg-cli` daemon 工作流作为当前事实。

## 当前真实能力

CLI 当前支持：

```bash
skillreg config
skillreg workspace create <path>
skillreg workspace current
skillreg workspace switch <path>
skillreg register <path> [--force] [--name name]
skillreg list
skillreg convert <name>
skillreg source npm preview <package> [--registry url] [--version-spec spec]
skillreg source npm import <package> [--mode skill|repo] [--skill name]
skillreg source list
skillreg source check <source-id>
skillreg source update-preview <source-id>
skillreg source update <source-id> [--dry-run] [--force]
skillreg target list
skillreg target add <path>
skillreg target remove <path>
skillreg target rename <old> <new>
skillreg sync status
skillreg sync execute --target <path> [--skill name] [--dry-run]
skillreg project create --name <name> --target <path>
skillreg project list
skillreg project info <name>
skillreg project add-target <name> <path>
skillreg project remove-target <name> <path>
skillreg project delete <name>
skillreg sync execute --project <name>
skillreg diff <skill> --target <path>
skillreg submodule list
skillreg dashboard open
skillreg dashboard start
skillreg dashboard status
skillreg dashboard stop
```

所有 Click help 都应同时支持 `-h` 和 `--help`。

API/backend 当前覆盖：

- workspace current/switch/create
- skill list/detail/file/tree/export
- registry register/convert
- import 本地目录/zip/git
- sources NPM preview/import/list/check/update-preview/update
- sync targets/projects/status/execute/diff/target file/remove
- submodule list/refresh/preview/diff/sync
- git history/status
- health/files/hooks 相关 dashboard 接口

Dashboard 是人类用户的主要操作入口；CLI 是 agent 自动化闭环入口。

## 代码组织

- `src/skillreg/cli.py`：CLI 入口和命令封装。
- `src/skillreg/server/`：FastAPI routes。
- `src/skillreg/services/`：业务逻辑。
- `src/skillreg/services/npm_source.py`：NPM registry、完整性、安全解包与 Skill 发现。
- `src/skillreg/services/source_store.py`：`.skillreg/sources.json` 原子存储与校验。
- `src/skillreg/services/source_manager.py`：来源导入、diff、更新事务与 Git 集成。
- `src/skillreg/builtin/skillreg-skill/`：注入 workspace 的内置 skill。
- `dashboard/src/`：Vue dashboard。
- `scripts/versioning.py`：版本同步、检查、bump 逻辑。
- `scripts/check_version.py`：CI/release 使用的版本一致性检查入口。
- `scripts/hooks/commit-msg`：本地 main 分支提交时的版本 bump hook。
- `scripts/release.sh`：本地创建并推送 release tag 的脚本。

## 开发规范

### 1. 以 workspace 模型为准

所有用户能力都围绕当前 `~/.skillreg/config.json` 指向的 workspace 展开。
用户可能在任意项目中说“注册这个 skill”，agent 应定位本地 `SKILL.md`
所在目录并注册到当前 workspace，而不是要求用户理解产品仓、workspace 仓或
agent-hub 旧结构。

### 2. 文档只写当前事实

- README 面向用户，保持简洁。
- AGENTS.md 面向后续 agent，写真实实现和工作流。
- 不要引用已删除的 `docs/archive/` 或迁移期 issue 作为当前事实来源。
- 不要恢复旧 daemon 命令描述，除非代码真的重新支持。

### 3. Sync 状态语义

当前后端同步状态主要是：

- `synced`：workspace 与 target 一致。
- `modified`：target 侧存在差异。
- `missing`：target 中缺少该 skill。

不要在新文档/UI 中引入未由后端实际返回的状态。

NPM 来源状态是独立维度，只使用 `up-to-date`、`update-available`、
`check-failed` 等来源语义，不得复用或扩展 target sync 状态。

### 4. NPM 来源安全边界

- NPM 只作为制品来源，不执行 `npm install` 或任何生命周期脚本。
- 通过 registry metadata 解析 tarball，校验 integrity，并在提供 shasum 时同时校验。
- 解包拒绝绝对路径、路径穿越、Windows 盘符、符号链接、硬链接和资源超限。
- Preview 只向客户端返回受管 session token，不返回或接受任意临时路径。
- Skill 模式只管理声明的 `skills/` 路径；Repo 模式只管理 manifest 声明的 `skills/` 和来源 manifest。
- 自动提交使用精确 pathspec，不推送 remote，不夹带已有 index 或 hook 产生的无关改动。

### 5. 版本元数据

版本号必须保持一致：

- `pyproject.toml` 的 `[project].version`
- `src/skillreg/__init__.py` 的 `__version__`
- `src/skillreg/builtin/skillreg-skill/SKILL.md` 的 `metadata.version`
- `uv.lock` 中 editable 包版本

检查：

```bash
uv run python scripts/check_version.py
```

如果需要手动同步指定版本：

```bash
uv run python scripts/versioning.py sync --version 1.2.3
```

### 6. Git hook

安装本地 hook：

```bash
scripts/install-git-hooks.sh
```

在 `main` 分支提交时，`commit-msg` hook 会根据提交信息 bump `x.y.z`：

- `feat:`：`y + 1`，`z` 归零。
- 其他提交：`z + 1`。
- `x` 固定为 `1`。

注意：当前 hook 会在 commit-msg 阶段修改并 `git add` 版本文件。若提交后
发现版本文件仍留在工作树，需要补一个 `chore: sync version <version>` 提交，
并使用 `--no-verify` 避免再次 bump。

## 发布工作流

本地发布入口：

```bash
scripts/release.sh
```

发布前脚本要求 working tree 干净，并执行：

1. `uv run python scripts/check_version.py`
2. 读取当前版本，生成 tag `v<version>`
3. 检查本地和远端不存在同名 tag
4. `git tag -a v<version> -m "Release v<version>"`
5. `git push origin main`
6. `git push origin v<version>`

推送 tag 后，GitHub Actions 的 `.github/workflows/release.yml` 会：

1. 安装依赖
2. `scripts/check_version.py --require-tag`
3. 跑测试
4. 构建 wheel/sdist
5. 校验构建产物版本
6. 上传 artifacts
7. 创建 GitHub Release
8. 发布到 PyPI

不要手工上传 PyPI 包；以 tag workflow 为准。

## 验证门禁

常规代码/文档变更后至少跑：

```bash
uv run python scripts/check_version.py
uv run pytest -q
uv run --with ruff ruff check src/ tests/ scripts/
```

涉及 CLI 命令面时，额外跑对应 help/命令：

```bash
uv run skillreg -h
uv run skillreg <group> -h
```

涉及 dashboard UI 时，再跑 dashboard 侧构建/验证。

## 对 agent 的要求

1. 先确认当前代码真实支持某项能力，再写 README、AGENTS.md 或 skill 文案。
2. 不要把旧 `skillreg-cli`、daemon、agent-hub 运行方式写成当前事实。
3. 对用户可见文案保持“本地 skill workspace”心智，不暴露不必要的仓库实现细节。
4. 提交前确认版本检查、测试和 lint。
5. 发布时使用 `scripts/release.sh`，不要绕过 tag workflow。
