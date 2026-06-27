# skillreg v2 — 架构升级 PRD

## 元信息

- **Status**: Draft
- **Created**: 2026-06-27
- **作者**: kexjhhuang（经 grill 决策收敛）
- **关联**: 决策固化见项目记忆 `skillreg-v2-architecture`；本文档替代 `todo/reusability-analysis.md`（v1 可复用化）作为 v2 上游基线
- **前置 spec**: `dashboard-architecture-v2.md`（v1，Node 架构，迁移参考）、`skill-version.md`、`ssh-remote.md`（v1.x）

---

## 1. 背景与动机

### 1.1 现状

agent-hub 当前把「infra 中控」和「skills 存储」捆绑在同一个仓库：

- `infra/sync-skills.py` 靠 `REPO_ROOT = SCRIPT_DIR.parent`（[sync-skills.py:24-25](../infra/sync-skills.py#L24-L25)）反推 skills 位置。
- `_resolve_repo_path`（[sync-skills.py:448-460](../infra/sync-skills.py#L448-L460)）**主动拒绝仓库外路径**——代码层面就堵死了「skill 存在外部仓库」的路。
- skills/ + repos/ 与 infra/ 同仓，导致上游同步复杂、个人下游（agent-hub-kex）难以干净分离。

### 1.2 痛点

| 痛点 | 根因 | 影响 |
|---|---|---|
| 上游同步复杂 | skills 存储与 infra 捆绑 | 下游 fork 后 merge upstream 易冲突 |
| 双语言运行时 | Node server + Python sync 引擎 | 用户需装 Node + 编译原生模块（better-sqlite3、node-pty） |
| 中控与存储耦合 | sync 引擎靠脚本位置反推 REPO_ROOT | 无法指向外部 workspace 仓库 |
| 品牌不统一 | agent-hub / skillreg-cli 混用 | 开源定位模糊 |
| kanban 渗透 server | kanban 是 agent/terminal 的执行臂根 | 砍 kanban 牵连 agent+terminal |

### 1.3 目标

1. **解耦**：skillreg（中控产品仓）与 workspace 仓库（skills 存储）分离。
2. **单语言**：server 从 Node 全迁 Python，用户装 `uv tool install skillreg` 即可，无 Node 依赖。
3. **品牌统一**：统一为 skillreg，移除 kanban。
4. **可开源**：新仓 greenfield，干净基线，可发布到 GitHub。

### 1.4 非目标

- 不保留 agent-hub git 历史（greenfield）。
- 不做双轨共存（迁移完成后旧仓归档）。
- v1 不含 ssh 远程能力（列 v1.x）。
- v1 不含 UI 框架通用化/多样化品牌加强（列 v1.x）。
- 不引入仓库级清单文件（`skillreg.json`）——保留任意摆放 + 扫描发现。

---

## 2. 目标架构

### 2.1 双仓库模型

```
skillreg/                              # 产品仓（中控，monorepo + submodule）
├── skillreg-cli/                      # submodule：配套 CLI（Python，uv 分发）
├── self-skill/                        # submodule：skillreg 自描述 skill
├── ui-framework/                      # submodule：UI 样式框架（v1.x 通用化/多样化）
├── server/                            # Python 后端（FastAPI）
├── dashboard/                         # Vue 前端（构建产物，由 server 托管）
├── specs/
└── pyproject.toml                     # monorepo 根包

<workspace>/                           # 用户 workspace 仓库（skills 存储，独立 git，可带 remote）
├── skills/                            # 零散 skill（强制存在）
├── repos/                             # 子模块型 skill
├── .skillreg/builtin/                 # 保留区：self-skill 注入目标（gitignore）
├── .gitattributes                     # 可预置
└── README.md
```

- 用户视角：skillreg 是一个 CLI。`skillreg dashboard open` 打开**已构建的前端+后端产物**。
- 初始为空：装完 skillreg 无任何 skill，用户 (a) 指向一个现有 workspace 仓库，或 (b) 在 dashboard 选本地位置创建一个。
- skillreg 大仓自身符合 skillreg 规范，可用 dashboard 把 skillreg 自己引入注册表（自举）。

### 2.2 扫描规范（skill 级，非仓库级）

- skillreg 认 `SKILL.md` 目录，仓库是装 skill 的袋子，**保留任意摆放 + 扫描发现能力**（差异化优势）。
- workspace 内 `skills/` 零散 + `repos/` 子模块，沿用当前布局。
- **不引入 `skillreg.json` 清单文件**。
- sync 引擎改动：`REPO_ROOT` 从「靠脚本位置反推」改为「用户配置指向的 workspace 路径」；`_resolve_repo_path` 的仓库外路径护栏相应放松（workspace 本来就在 skillreg 之外）。

### 2.3 配置归属

| 配置项 | 归属 | 位置 |
|---|---|---|
| skills/ 内容、repos/ 子模块 | workspace 仓库 | workspace 根 |
| 安装 targets（`~/.claude/skills` 等） | skillreg 本地 | `~/.skillreg/config.json` |
| agent 约定（claude/codebuddy/codex…） | skillreg 本地 | `~/.skillreg/config.json` |
| workspace 指针 | skillreg 本地 | `~/.skillreg/config.json` |
| exclude 规则、manifest 设置 | skillreg 内置默认 | 代码内置 |

- workspace 仓库**不再有** `sync-skills.json`、不再有 `infra/`。
- 当前 `sources` 白名单**消失**（它仅因 infra/ 被排除却要导入 self-skill 而存在，解耦后无此需求）。

### 2.4 self-skill

- 构建产物打包：Python 包内带 `skillreg_cli/builtin/skillreg/SKILL.md`，用 `importlib.resources` 读取。
- skillreg 启动时更新到 workspace 的 `.skillreg/builtin/skillreg/`（保留区，**gitignore，不进 workspace git**）。
- scan 完全复用通用扫描逻辑（`.skillreg` 不在 exclude 列表），零特例链路。
- self-skill 作为 skillreg 大仓的并列 submodule 之一。

### 2.5 品牌与范围

- 统一命令为 **skillreg**；skillreg-cli 是配套 CLI（submodule）。
- skillreg 承担原 dashboard / server / daemon 职责。
- **移除 kanban**，连带砍掉 agent + terminal（它们依赖 `kanban.js` 的 `getDb`/`updateTask`，是 kanban 的执行臂，kanban 砍了即成孤儿）。
- **保留 ssh** 远程能力（独立模块，不和 kanban 耦合）——但列为 **v1.x**。

---

## 3. 技术栈迁移（模型 B）

### 3.1 决策

- server 从 Node（Hono.js）全迁 **Python（FastAPI/Starlette）**。
- dashboard 构建成静态文件，Python 后端 `StaticFiles` 托管 + 提供 API。
- 用户装 `uv tool install skillreg` 即完事，无需 Node。
- **路径 B：新仓一次性 Python 重写**，不搞双运行时并存。
- 旧 agent-hub 仓迁移期间继续可用，新仓覆盖全部 v1 域 + dashboard 跑通后才切换。

### 3.2 降风险方式：契约冻结 + 垂直切片

1. **契约冻结**：把 v1 全部 route 域的 request/response 结构写成 `specs/api-contract.md`（OpenAPI schema），作为前后端共同契约。这一步不写代码，只沉淀现状。
2. **垂直切片迁移**：按 route 域独立迁，每迁完一个域（Python service + 对应前端 API 调用 + 验证）就是一次可验证的小里程碑。
3. **前端复用**：13000 行 Vue 不重写，从 agent-hub `dashboard/` 整体复制后改，只改 `api/index.js` 适配层。UI 组件基本不动。
4. **sync 权威复用**：`sync-skills.py` 作为 sync 逻辑唯一权威，新 Python 后端 import 当库用，不重抄。

### 3.3 迁移真实分布

关键发现：Node server 里 **sync 和 hooks 两个域只是 Python 脚本的 subprocess 转发壳**——
- `sync-manager.js:32` `spawn('python3', [SYNC_SCRIPT, ...])` 转发给 `sync-skills.py`。
- `hook-manager.js:5` `execFile('python3', [HOOKS_CLI, ...])` 转发给 `infra/hooks.py`。

迁移时这两个壳**直接删除**，后端 import Python 库即可，0 重抄。这也再次印证 skillreg-cli 与 agent-hub 强耦合的根因就在这层 spawn 转发。

| 域 | 模式 | v1 归属 | 迁移量 |
|---|---|---|---|
| sync | Python 权威 + Node 壳 | v1 | 壳删除，import sync-skills.py，0 重抄 |
| hooks | Python 权威 + Node 壳 | v1 | 壳删除，import hooks.py，~0 |
| files | Node 原生 | v1 | 重写 ~150 行（`pathlib`+`os.walk`） |
| git | Node 原生（薄） | v1 | 重写 ~70 行 + 基准切换 |
| import | Node 原生（重） | v1 | 重写 ~520 行（zip/git/本地 × skill/submodule + update） |
| registry | Node 原生（最重） | v1 | 重写 ~552 行（`getAll()` 超级聚合，契约最厚） |
| submodules | Node 原生 | v1 | 重写（submodule-manager.js ~310 行） |
| skills | Node 原生 | v1 | 重写（routes/skills.js ~163 行） |
| ssh | Node 原生（独立重） | **v1.x** | ~740 行 |
| UI 品牌加强 | — | **v1.x** | UI 框架通用化/多样化 |

### 3.4 sync 权威归属

- `sync-skills.py` 是 sync 逻辑唯一权威（Node `sync-manager.js` 只是 subprocess 转发壳，删除即可）。
- `sync-manager.js` 的三块 Node 独有职责迁入 Python 后端：
  1. 配置 CRUD（`getConfig`/`addTarget`/`removeTarget`/`renameTarget`/`writeConfig`）——迁入 `~/.skillreg/config.json` 管理。
  2. project 注册表（`~/.skillreg/projects.json` CRUD）——迁入 Python。
  3. agent 目录发现（`discoverAgentDirs`/`discoverHomeAgentDirs`）——`sync-skills.py:688-706` 已有等价实现 `discover_agent_hub_dirs`，直接复用，Node 版删除。

---

## 4. 契约冻结高危清单（迁移时不得丢失/简化）

### 4.1 registry 域 `getAll()` 返回结构原样冻结

`skill-registry.js` 的 `getAll()`（[:427-535](../infra/server/services/skill-registry.js#L427-L535)）一次返回 `{ skills, repoNodes, submodules, relationships, generatedAt }`，含大量派生计算，前端 20 个 fetch 中相当部分依赖此结构。必须原样冻结：

- **graphType 四态**：`isolated-skill` / `cli-skill` / `repo-cli` / `repo-skill`（[:459-472](../infra/server/services/skill-registry.js#L459-L472)）。
- **`skill/` 子路径约定**：判定 `cli-skill` 靠 skill 目录是否在 submodule 的 `skill/` 子路径下——隐式契约，前端依赖画树。
- **submodule 指针字段**：`indexRef`/`indexAhead`/`indexBehind`/`indexDirty`（[:343-380](../infra/server/services/skill-registry.js#L343-L380)）。`indexDirty` 是曾踩过的坑（"preview 说已是最新但 sync 还在更新指针"），**不得当冗余砍掉**。
- **syncState 七态**：`synced`/`ahead`/`behind`/`diverged`/`dirty`/`missing`/`unknown`。
- **repoNodes 合成**：为每个有子 skill 的 submodule 合成 `isSubmoduleRoot` 节点（[:499-528](../infra/server/services/skill-registry.js#L499-L528)）。
- **清理 DEBUG 残留**：[:508-510](../infra/server/services/skill-registry.js#L508-L510) `if (sub.path.includes('ntdev')) console.error(DEBUG...)` 必须清除。

### 4.2 target 解析三函数统一为显式三态语义

当前三套解析逻辑、三种 fallback 行为，前端靠 `custom`→实际路径 remap 对齐：

- `resolveTargetArg`（sync-manager.js:192）——named 用名字，否则当 raw path。
- `_resolve_target_by_name_or_path`（sync-skills.py:675）——named 匹配，否则"看起来像路径"才当 raw path。
- `resolve_targets_for_sync`（sync-skills.py:709）——只匹配 named，raw path 走 agent 目录自动发现，发现不到才 fallback。

**统一为显式三态**：`named target` / `raw path` / `agent-dir 自动发现`，消除"看起来像路径"启发式。否则 `--target` 行为差异会在 Python 重写中悄然改变。

### 4.3 URL 规范化收成单一 lib

- `sshToHttps`（skill-registry.js:26）与 `resolveRepoUrl`（remote-syncer.js:187）是**两份独立的 URL 规范化实现**。
- v1 即收成单一 lib（放 `server/lib/url.py`），为 v1.x ssh 铺路，避免重演"sync 两份实现"。

---

## 5. v1 边界（开源可发布）

### 5.1 v1 必须跑通

完整闭环：**空 workspace → 导入 skill → 浏览 → 同步**。

- CLI 装载（`uv tool install skillreg`）
- `skillreg dashboard open`（打开已构建前后端产物）
- workspace 指针配置（`~/.skillreg/config.json`）
- workspace 创建（dashboard / CLI 触发 `git init`，强制 `skills/` 存在，可预置 `.gitattributes`）
- 扫描 skills（skill 级规范，任意摆放）
- sync 到 targets（复用 `sync-skills.py`）
- **project 组管理**（多 target 绑成项目组，一次 sync 同步到组内所有目录；后端即 `sync-manager.js` 的 `~/.skillreg/projects.json` 注册表，前端 `ProjectManager.vue` 759 行）
- files 浏览（文件树 + 内容预览）
- git 日志（主仓 + submodule）
- hooks（scan/status/install/uninstall/validate，复用 `hooks.py`）
- import 全能力（zip / git-clone / 本地目录 × skill / submodule 模式 + update 流程）
- registry / submodules / skills 域

### 5.2 v1.x

- ssh 远程能力（inventory + remote-syncer，~740 行迁 Python；含前端 `SshModeBanner`）
- UI 框架通用化 / 多样化品牌加强

### 5.3 前端组件与域映射（拆 issues 用）

v1 dashboard 从 agent-hub `dashboard/` 整体复制后改 `api/index.js`，组件基本不动。组件归属：

| 组件 | 域 | 备注 |
|---|---|---|
| SkillGrid / SkillCard / SkillDetailModal / SkillDetailDrawer / SkillContextPanel / DependencyGraph | registry/skills | DependencyGraph 画 `getAll()` relationships，依赖 4.1 契约 |
| SkillSyncManager(2799) / SkillSyncStatus / SkillSyncBadge / QDiffViewer | sync | SkillSyncManager 是最大单体组件 |
| ProjectManager(759) | sync（project 组） | 5.1 已列 |
| SkillImportModal(1265) | import | |
| SubmoduleStatus(1275) / SubmoduleBadge | submodules | |
| FileTree / FilePreview | files | |
| GitLog | git | |
| HooksView / HookItem | hooks | |
| CommandPanel(348) | 跨域命令聚合 | 需在 M4 确认调用的 API 范围 |
| SshModeBanner | ssh | **v1.x**，v1 移除/隐藏 |
| ComponentPlayground(453) | — | 组件演示页，v1 保留供开发，不进发布版 |
| Q* 前缀 + ThemeSwitch + NavItem + QLayout | UI 框架 | **v1 原样复制使用**；v1.x 抽进 `ui-framework` submodule 做通用化/多样化 |

**Q 组件张力**：v1 dashboard 要跑通就必须能用这些 Q 组件，但它们的"通用化/多样化改造"是 v1.x。结论：v1 原样复制现有 Q 组件进 skillreg 仓，v1.x 再抽进 `ui-framework` submodule。

### 5.4 旧仓处理

- 新 skillreg 仓 **greenfield**，不保留 agent-hub git 历史。
- 旧 agent-hub 仓迁移期间继续可用（只读维护，仅接 bugfix）。
- 新仓 v1 跑通 + agent-hub-kex 完成迁移后，旧仓**归档**（不双轨共存）。

### 5.5 agent-hub-kex 迁移路径

agent-hub-kex（个人下游）的迁移是独立工作项：
- 把 agent-hub-kex 的 `skills/` + `repos/` 内容搬进一个新的 workspace 仓库。
- 安装 skillreg，配置 `~/.skillreg/config.json` 指向该 workspace。
- 与 skillreg 仓的 git 历史无关。

---

## 6. 里程碑（垂直切片顺序）

按依赖排序，每域迁完即可验证：

| # | 里程碑 | 域 | 验证标准 |
|---|---|---|---|
| M0 | 契约冻结 | — | `specs/api-contract.md`（OpenAPI）覆盖 v1 全部 route |
| M1 | 仓库骨架 + CLI 装载 | — | greenfield skillreg 仓，`uv tool install skillreg` 可装，`skillreg config` 可跑 |
| M2 | workspace 指针 + 扫描 + sync | sync, skills, registry | 空 workspace → 扫描出 skill → sync 到 `~/.claude/skills` |
| M3 | workspace 创建 + import | import | dashboard 创建 workspace（git init + skills/ 骨架）；zip/git/本地导入 skill |
| M4 | 浏览与历史 | files, git, submodules, hooks | 文件树预览、git 日志、submodule 状态、hooks 安装 |
| M5 | dashboard 打通 | — | `dashboard open` 打开构建产物，前端 api/index.js 适配完成，v1 闭环跑通 |
| M6 | 开源发布 | — | README、LICENSE、CI、agent-hub-kex 迁移验证、旧仓归档 |

---

## 7. 风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| `getAll()` 契约迁移丢字段 | 前端树/状态展示错乱 | M0 契约冻结 + 4.1 清单逐字段核对 |
| target 解析三态语义漂移 | sync 行为静默改变 | 4.2 统一为显式三态，迁移时写对比测试 |
| import 重写量大（~520 行） | M3 拖期 | 优先 git-clone + 本地目录 + skill 模式；zip/submodule/update 可后置到 M3.5 |
| Node→Python 原生模块缺口 | 无（迁 Python 即消除） | 模型 B 本就为此 |
| agent-hub-kex 迁移阻断 | 旧仓无法归档 | M6 单列工作项，workspace 仓库独立可迁 |
| self-skill 注入与 scan 冲突 | `.skillreg/builtin/` 被误排除 | 确保 `.skillreg` 不在 exclude 列表（迁移约束） |

---

## 8. 待定 / 后续

- UI 框架 submodule 的具体通用化/多样化方案（v1.x 单独立项）。
- ssh 远程能力的 Python 实现（v1.x，优先评估"workspace git remote + 各机 git pull"是否已够用）。
- `specs/api-contract.md` 的 OpenAPI 细节（M0 产出）。

---

## 9. 决策溯源

本文档由 grill 流程收敛，九个根分叉的讨论过程见会话记录，结论固化于项目记忆 `skillreg-v2-architecture`。关键非显然事实：

> Node server 里 sync 和 hooks 两个域只是 Python 脚本的 subprocess 转发壳——这让"5200 行 Node 全迁 Python"的真实工作量大幅缩水，也坐实了 skillreg-cli 与 agent-hub 强耦合的根因就在这层 spawn 转发。
