# sync + registry + skills 域迁 Python（核心扫描与同步闭环）

## What to build

把 agent-hub 的 sync / registry / skills 三个域从 Node 迁到 Python，打通"扫描 workspace 里的 skill → 同步到 targets → dashboard 展示"核心闭环。这是 skillreg v1 的心脏。

**sync 域**：
- `sync-skills.py`（来自 `infra/sync-skills.py`）作为 sync 逻辑**唯一权威**，作库 import，不重抄。
- 迁 `sync-manager.js` 的 Node 独有职责到 Python：配置 CRUD（`getConfig`/`addTarget`/`removeTarget`/`renameTarget`）、project 注册表（`~/.skillreg/projects.json` CRUD）。
- agent 目录发现复用 `sync-skills.py` 的 `discover_agent_hub_dirs`，删除 Node 版。
- **target 解析统一为显式三态**（PRD 4.2）：`named target` / `raw path` / `agent-dir 自动发现`，消除"看起来像路径"启发式。统一当前三套逻辑（`resolveTargetArg` / `_resolve_target_by_name_or_path` / `resolve_targets_for_sync`）。
- sync 引擎 `REPO_ROOT` 改为用户配置的 workspace 路径；放松 `_resolve_repo_path` 仓库外路径护栏（workspace 在 skillreg 之外）。

**registry/skills 域**：
- 迁 `skill-registry.js` 的 `getAll()` 到 Python，**返回结构原样冻结**（PRD 4.1）：`graphType` 四态、`skill/` 子路径约定、`indexRef`/`indexAhead`/`indexBehind`/`indexDirty` 指针字段、`syncState` 七态、`repoNodes` 合成（`isSubmoduleRoot`）。
- 清除 `getAll()` 里 ntdev DEBUG 残留（skill-registry.js:508-510）。
- skill 分类（`classifySkillType`：CLI vs Reference，靠向上找 `pyproject.toml`/`src/*.py`）迁 Python。

**URL 规范化**（PRD 4.3）：合并 `sshToHttps`（skill-registry.js:26）+ `resolveRepoUrl`（remote-syncer.js:187）为单一 `server/lib/url.py`，为 v1.x ssh 铺路。

**前端适配**：从 agent-hub `dashboard/` 复制 `SkillSyncManager`/`SkillSyncStatus`/`SkillSyncBadge`/`QDiffViewer`/`SkillGrid`/`SkillCard`/`SkillDetailModal`/`SkillDetailDrawer`/`SkillContextPanel`/`DependencyGraph`/`ProjectManager`，只改 `api/index.js` 适配新 Python 后端契约（契约见 #1）。

来源代码：`infra/sync-skills.py`、`infra/server/services/sync-manager.js`、`infra/server/services/skill-registry.js`、`infra/server/routes/sync.js`、`infra/server/routes/skills.js`、`infra/server/routes/registry.js`、`infra/dashboard/src/api/index.js`。

## Acceptance criteria

- [ ] sync-skills.py 作库 import，REPO_ROOT 取自 workspace 配置
- [ ] sync 配置 CRUD + project 注册表在 Python 后端可用，存 `~/.skillreg/`
- [ ] target 解析为显式三态，三套旧逻辑统一，无"看起来像路径"启发式
- [ ] `getAll()` Python 版返回结构与契约 #1 完全一致（graphType 四态、indexDirty、repoNodes、syncState 七态等）
- [ ] ntdev DEBUG 残留已清除
- [ ] URL 规范化收成单一 `server/lib/url.py`，registry 显示的 remoteUrl 与原行为一致
- [ ] dashboard 显示 skill 列表 + 依赖关系图（DependencyGraph）+ submodule 状态
- [ ] dashboard 显示 sync 状态、执行 sync、管理 project 组
- [ ] 配置归属符合 PRD 2.3（workspace 只放 skills/+repos/，配置在 `~/.skillreg/config.json`，sources 白名单消失）

## Blocked by

- #1（API 契约）
- #2（仓骨架 + Python 后端框架）
