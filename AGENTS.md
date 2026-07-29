# AGENTS.md

## 项目定位

`skillreg` 是本地 AI Agent Skill 管理工具，同时发布为 PyPI 包和 npm 包
`skillreg`。npm 包是轻量启动器，运行相同版本的 Python 核心。

当前项目由三部分组成：

- **CLI**：`skillreg` 命令，面向 agent 和开发者的自动化入口。
- **FastAPI backend**：Dashboard 和兼容接口的服务层。
- **Dashboard**：面向人类用户的图形管理入口。

管理对象是用户本地的 skill workspace。workspace 通常只包含：

- `skills/`：直接注册进 workspace 的 skills。
- `repos/`：转换为子仓/CLI 骨架后的 skills。

所有产品说明和实现判断都以当前 workspace、CLI、backend 和 Dashboard
架构为准。

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
- `npm/`：npm CLI 启动器、隔离 Python 运行时引导和 npm 包测试。
- `scripts/versioning.py`：版本规划、同步和一致性检查。
- `scripts/check_version.py`：CI/release 使用的版本一致性检查入口。
- `scripts/check_release_state.py`：发布前只读核对 Git remote、PyPI 和 npm 状态。
- `scripts/hooks/commit-msg`：受管的只读 hook，不修改工作树或 index。
- `scripts/release.sh`：本地预览、验证并执行 release commit/tag/push 的入口。

## 开发规范

### 1. 以 workspace 模型为准

所有用户能力都围绕当前 `~/.skillreg/config.json` 指向的 workspace 展开。
用户可能在任意项目中说“注册这个 skill”，agent 应定位本地 `SKILL.md`
所在目录并注册到当前 workspace，不要求用户理解内部仓库划分。

### 2. 文档只写当前事实

- README 面向用户，保持简洁。
- AGENTS.md 面向后续 agent，写真实实现和工作流。
- 不要引用已删除的文档或历史 issue 作为当前事实来源。
- 不要在当前文档中保留已经退出产品模型的架构、命令或品牌描述。
- README 只保留产品定位、安装方式、最短使用闭环和开发入口，不维护完整命令清单；CLI 命令和参数以 `-h` / `--help` 为准。
- `README.md` 与 `docs/README.en.md` 的结构、能力边界和关键入口必须同步维护。
- `docs/` 只保存需要长期维护的用户指南或维护者手册。新增文档前先检索现有内容，优先合并，避免产生重复事实源。
- 临时方案、执行交接和已解决事故记录不得长期留在 `docs/`；任务完成后应删除临时文档，历史结论由 issue、commit 和 Git history 承载。
- 跟踪文档不得记录个人机器的绝对路径、一次性工作区状态或仅对单次执行有效的恢复步骤。

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
- `npm/package.json` 和 `npm/package-lock.json` 的版本
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

普通 `fix:`、`feat:`、`chore:` 等提交不会修改版本文件。受管
`commit-msg` hook 只保留稳定的提交入口，不修改工作树或 index。安装脚本可
替换旧版 skillreg 受管 hook；若发现无法确认来源的自定义 hook，会停止并要求
人工处理，不会覆盖。

## 发布工作流

先只读预览：

```bash
scripts/release.sh --dry-run
```

脚本使用最近一个 `HEAD` 可达的 `vX.Y.Z` tag，分析 `tag..HEAD` 的全部
Conventional Commits：

- `BREAKING CHANGE:` 或 header 中的 `!`：major。
- `feat:`：minor。
- `fix:`、`perf:`、`revert:`：patch。
- 其他类型默认不触发发布。

同一区间只取最高等级并 bump 一次。没有可发布变更时自动发布会停止；维护者可
使用 `--bump patch|minor|major` 显式覆盖。`plan` 和 `prepare` 也可独立使用：

```bash
python3 scripts/versioning.py plan --json
python3 scripts/versioning.py prepare
```

正式发布运行 `scripts/release.sh`。脚本要求 `main`、干净工作树、完整且一致的
本地/远端 tag，并只读核验 PyPI 与 npm。确认后执行：

1. 同步 6 个版本元数据文件（包括 `uv.lock`）。
2. 执行版本检查、Python 测试和 lint、Dashboard 测试/构建/E2E、npm 测试和 pack。
3. 精确暂存版本文件并创建唯一的 `chore(release): vX.Y.Z` 提交。
4. 创建 annotated tag。
5. 原子 push `main` 和 tag。

任何验证失败都不会创建 tag 或 push，已生成的版本差异会保留供审查。迁移期若
源码版本高于最近 tag 且不低于提交区间要求的最低版本，计划会沿用该 pending
version；不会降级或重复 bump。

推送 tag 后，GitHub Actions 的 `.github/workflows/release.yml` 会：

1. 安装依赖
2. `scripts/check_version.py --require-tag`
3. 跑测试
4. 构建 wheel/sdist
5. 校验构建产物版本
6. 上传 artifacts
7. 创建 GitHub Release
8. 发布到 PyPI
9. 发布到 npm

不要手工上传 PyPI 或 npm 包；首次占用 npm 包名除外，后续以 tag workflow
为准。release workflow 使用完整 Git 历史验证 tag 与版本一致性。npm 首次发布
和 Trusted Publishing 配置见 `docs/npm-publishing.md`。

## 验证门禁

常规代码/文档变更后至少跑：

```bash
uv run python scripts/check_version.py
uv run pytest -q
uv run --with ruff ruff check src/ tests/ scripts/
(cd npm && npm ci && npm test && npm pack --dry-run)
```

涉及 CLI 命令面时，额外跑对应 help/命令：

```bash
uv run skillreg -h
uv run skillreg <group> -h
```

涉及 dashboard UI 时，再跑 dashboard 侧构建/验证。

## 对 agent 的要求

1. 先确认当前代码真实支持某项能力，再写 README、AGENTS.md 或 skill 文案。
2. 只描述当前 workspace、CLI、backend 和 Dashboard 实际支持的运行方式。
3. 对用户可见文案保持“本地 skill workspace”心智，不暴露不必要的仓库实现细节。
4. 提交前确认版本检查、测试和 lint。
5. 发布时使用 `scripts/release.sh`，不要绕过 tag workflow。
