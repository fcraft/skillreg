# skillreg v1 API 契约（冻结）

> 本文档冻结 agent-hub v1 全部 route 域的 request/response 结构，作为 skillreg Python 后端重写与前端适配的共同地基。
> 详细逐域契约见 `specs/_contract_parts/` 下的分域文档。
> 机读版本见 `specs/openapi.yaml`。

## 覆盖域

| 域 | 分域文档 | 迁移模式 | 迁移量 |
|---|---|---|---|
| sync | [sync.md](_contract_parts/sync.md) | Python 权威 + Node 壳删除 | 0 重抄（import sync-skills.py） |
| registry | [registry-skills.md](_contract_parts/registry-skills.md) | Node 原生重写 | ~552 行（getAll 超级聚合） |
| skills | [registry-skills.md](_contract_parts/registry-skills.md) | Node 原生重写 | ~163 行 |
| import | [import-git-submodules.md](_contract_parts/import-git-submodules.md) | Node 原生重写 | ~520 行 |
| files | [files.md](_contract_parts/files.md) | Node 原生重写 | ~150 行 |
| git | [import-git-submodules.md](_contract_parts/import-git-submodules.md) | Node 原生重写 | ~70 行 |
| submodules | [import-git-submodules.md](_contract_parts/import-git-submodules.md) | Node 原生重写 | ~310 行 |
| hooks | [hooks.md](_contract_parts/hooks.md) | Python 权威 + Node 壳删除 | ~0（import hooks.py） |

## 高危契约清单

### 1. registry 域 `getAll()` 聚合结构

`getAll()` 一次返回 `{ skills, repoNodes, submodules, relationships, generatedAt }`，前端 20 个 fetch 中相当部分依赖此结构。**必须原样冻结**：

- **graphType 四态**：`isolated-skill` / `cli-skill` / `repo-cli` / `repo-skill`
  - `cli-skill` 判定：skill 目录在 submodule 的 `skill/` 子路径下（隐式契约）
- **submodule 指针字段**：`indexRef` / `indexAhead` / `indexBehind` / `indexDirty`
  - `indexDirty` 曾踩坑（"preview 说已是最新但 sync 还在更新指针"），**不得当冗余砍掉**
- **syncState 七态**：`synced` / `ahead` / `behind` / `diverged` / `dirty` / `missing` / `unknown`
- **repoNodes 合成**：为每个有子 skill 的 submodule 合成 `isSubmoduleRoot` 节点
- **Skill 对象全字段**（冻结）：`id, name, description, type, graphType, parentNode, path, skillFilePath, fileCount, remoteUrl, parentSkill(恒null), isSubmodule, submodulePath`
- **RepoNode 全字段**（合成）：`id, name, description, type, graphType, parentNode(null), path, skillFilePath(null), fileCount(0), remoteUrl, parentSkill(null), isSubmodule(true), submodulePath, isSubmoduleRoot(true), branch`
- **indexDirty 字段闭合缺口**（迁移必修）：v1 `getSubmoduleStatus` 目录不存在分支（skill-registry.js:306）**漏了 `indexDirty`**，仅 catch 分支（:335）才有 → Python 版须统一补齐 `indexDirty`
- **ntdev DEBUG 残留**：`skill-registry.js:508-510` 的 `console.error(DEBUG...)` **必须清除**
- **classifySkillType**：`CLI` vs `Reference`，从 skillDir 向上逐级找 `pyproject.toml` 或 `src/*.py`

详见 [registry-skills.md](_contract_parts/registry-skills.md)。

### 2. target 解析三态语义

当前三套解析逻辑、三种 fallback 行为：

| 函数 | 位置 | 行为 | 启发式 |
|---|---|---|---|
| `resolveTargetArg` | sync-manager.js:192 | named 否则原样当 raw path | 无 |
| `_resolve_target_by_name_or_path` | sync-skills.py:675 | named 否则"看起来像路径"才当 raw path | **有**（`'/' in value or '~' in value`） |
| `resolve_targets_for_sync` | sync-skills.py:709 | 只 named + agent-dir 自动发现 + fallback | 无（但多 target） |

**统一为显式三态**：`named target` / `raw path` / `agent-dir 自动发现`，消除"看起来像路径"启发式。

详见 [sync.md](_contract_parts/sync.md)。

### 3. URL 规范化

- `sshToHttps`（skill-registry.js:26）与 `resolveRepoUrl`（remote-syncer.js:187）是**两份独立的 URL 规范化实现**。
- v1 收成单一 `server/lib/url.py`，为 v1.x ssh 铺路。

### 4. hooks 域现状契约缺口

- `installHook` / `uninstallHook` 前端发送 `{ hookId }` 但后端读 `{ id }` → **当前不可用**。
- `validateHooks` 前端用 `GET` 但后端是 `POST`，且 hooks.py validate 分支无 `--json` 输出 → **恒定 500**。
- 迁移时修复这些缺口。

详见 [hooks.md](_contract_parts/hooks.md)。

### 5. git 域内嵌载体（迁移易漏）

- `/api/git/logs` 是**孤儿端点**（前端 `fetchGitLogs` 导出但从不调用）；dashboard 实际通过 `/api/skills?full=1` 与 `/api/skills/refresh` 里**内嵌的 `gitLogs` 字段**取日志（`getLogs('all')` 硬编码）。
- 迁移时**两条载体都要保留**，否则 GitLog.vue / SubmoduleStatus.vue 变空。
- `getLogs` 用空 `catch{}` 吞错——缺失 submodule key 是常态非错误，前端已防御性 `|| []`，Python 版须保留宽松语义。
- `CommitEntry = { hash(%H 全 SHA), message(%s subject), author(%an 名非邮箱), date(%aI 严格 ISO) }`；main ≤15 条，每 submodule ≤10 条。

### 6. submodules 域 dirty 语义不一致（迁移须统一）

- `getSubmoduleStatus.dirty`：`porcelain.length > 0`（**含 untracked**）
- `previewSyncSubmodule.dirty`：仅 tracked（过滤 untracked）
- `syncSubmodule` 内部 dirty：含 untracked，但 `git add -u` 只 add tracked → 仅 untracked 时 staged 空 → 不 commit
- `commitMessage` v1 字符串拼接有注入风险，Python 版**必须用参数数组**。
- 错误响应体 v1 不统一：`GET /` 与 `refresh` 仅 `{error}`，其余 `{error, success:false}`；`fix-detached` 成功响应缺 `success`。迁移时统一 schema。

详见 [import-git-submodules.md](_contract_parts/import-git-submodules.md)。

## v1.x 移除域（不在 v1 范围）

| 域 | 状态 | 备注 |
|---|---|---|
| ssh | v1.x 移除 | ~740 行，含 `SshModeBanner` |
| kanban | v1.x 移除 | 连带 agent + terminal |
| agent | v1.x 移除 | 依赖 kanban |
| terminal | v1.x 移除 | 依赖 kanban |
| compat | v1.x 移除 | 兼容层 |

## 基准路径迁移

所有域的基准从 `REPO_ROOT`（靠脚本位置反推）切换为 **用户配置的 workspace 路径**（`~/.skillreg/config.json` 的 `workspace_path`）。

- `sync-skills.py` 的 `REPO_ROOT` → workspace 路径
- `_resolve_repo_path` 的仓库外路径护栏 → 放松（workspace 本来就在 skillreg 之外）
- `paths.js` 的 `REPO_ROOT` → workspace 路径
- `CONFIG_PATH`（`infra/sync-skills.json`）→ `~/.skillreg/config.json`（targets/agents/workspace 指针）

## 配置归属迁移

| 配置项 | v1（agent-hub） | v1（skillreg） |
|---|---|---|
| skills/ 内容 | workspace 仓库 | workspace 仓库（不变） |
| repos/ 子模块 | workspace 仓库 | workspace 仓库（不变） |
| sync targets | `infra/sync-skills.json` | `~/.skillreg/config.json` |
| agent 约定 | `infra/agent-conventions.json` | `~/.skillreg/config.json` |
| workspace 指针 | 无（靠脚本位置反推） | `~/.skillreg/config.json` |
| sources 白名单 | `infra/sync-skills.json` | **消失**（全量扫描发现） |
| exclude 规则 | `infra/sync-skills.json` | 代码内置默认 |
| project 注册表 | `~/.skillreg/projects.json` | `~/.skillreg/projects.json`（不变） |
