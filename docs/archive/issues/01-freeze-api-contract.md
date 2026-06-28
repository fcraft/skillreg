# 冻结 v1 API 契约为 OpenAPI

## What to build

把现有 agent-hub（`/Users/kex/Code/project_kex/agent-hub`）v1 全部 route 域的 request/response 结构逆向成正式 API 契约文档，作为 skillreg Python 后端重写与前端适配的共同地基。

这一步**不写任何代码**，只沉淀现状契约。产出 `specs/api-contract.md`（人读）+ `specs/openapi.yaml`（机读）。

覆盖 v1 全部域：sync / hooks / files / git / import / registry / submodules / skills。

**必须精确冻结的三处高危契约**（见 `specs/skillreg-v2.md` 第 4 章）：

1. **registry 域 `getAll()` 聚合结构**：一次返回 `{ skills, repoNodes, submodules, relationships, generatedAt }`，含：
   - `graphType` 四态：`isolated-skill` / `cli-skill` / `repo-cli` / `repo-skill`
   - `skill/` 子路径约定（判定 `cli-skill` 的隐式契约）
   - submodule 指针字段：`indexRef` / `indexAhead` / `indexBehind` / `indexDirty`（`indexDirty` 曾踩坑，不得当冗余）
   - `syncState` 七态：`synced` / `ahead` / `behind` / `diverged` / `dirty` / `missing` / `unknown`
   - `repoNodes` 合成（`isSubmoduleRoot`）
2. **target 解析三态语义**：当前三套解析逻辑（`resolveTargetArg` / `_resolve_target_by_name_or_path` / `resolve_targets_for_sync`）要逆向清楚，标注各自的 fallback 行为，为后续统一为显式三态（named / raw-path / agent-dir 自动发现）做准备。
3. **URL 规范化**：`sshToHttps`（skill-registry.js:26）与 `resolveRepoUrl`（remote-syncer.js:187）两份实现的输入输出。

来源代码：`infra/server/routes/*.js`、`infra/server/services/*.js`、`infra/sync-skills.py`、`infra/dashboard/src/api/index.js`。

## Acceptance criteria

- [ ] `specs/api-contract.md` 覆盖 v1 全部 8 个 route 域的 request/response 结构
- [ ] `specs/openapi.yaml` 可被工具校验通过（如 `swagger-cli validate`）
- [ ] `getAll()` 返回结构的每个字段都有记录，含 graphType 四态、syncState 七态、indexDirty 等指针字段
- [ ] target 解析三套逻辑的差异已文档化，并标注统一的显式三态目标
- [ ] URL 规范化两份实现的输入输出已记录
- [ ] 标注 `getAll()` 中需清理的 ntdev DEBUG 残留（skill-registry.js:508-510）

## Blocked by

None - can start immediately
