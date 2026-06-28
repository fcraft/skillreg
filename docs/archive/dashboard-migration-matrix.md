# Dashboard Migration Matrix

## Goal

将 `agent-hub/infra/dashboard` 的 Dashboard UI 与相关后端能力迁移到 `skillreg`，明确排除以下域：

- hooks
- ssh

本矩阵以 `agent-hub` 现有 Vue Dashboard 的实际调用面为准，定义：

- 哪些页面需要迁移
- 每个页面依赖哪些 API
- `skillreg` 当前是否已具备对应能力
- 建议的迁移动作与优先级

## Scope

### In Scope

- Skill 列表 / 详情 / 文件树 / 文件预览 / 导出
- Sync 工具与目标管理
- 项目组管理
- 仓库状态 / submodule 管理
- 依赖关系图
- Git 日志
- Import 流程
- 组件实验室（可选，低优先级）
- Dashboard Vue UI 框架本身（布局、主题、命令面板、提示、详情弹层）

### Out of Scope

- Hooks 页面与相关 API
- SSH 页面与相关 API
- Agent session / task dispatch / tmux / PTY
- Kanban 页面与 API

## UI Route Matrix

| Route | Source Component | Keep | Notes |
|---|---|---:|---|
| `/skills` | `SkillGrid.vue` | Yes | 主页面，必须迁移 |
| `/sync` | `SkillSyncManager.vue` | Yes | 依赖最多，优先补 API |
| `/projects` | `ProjectManager.vue` | Yes | 项目组能力保留 |
| `/repos` | `SubmoduleStatus.vue` | Yes | Submodule 视图保留 |
| `/graph` | `DependencyGraph.vue` | Yes | 基于 relationships / repoNodes |
| `/logs` | `GitLog.vue` | Yes | 依赖 git logs |
| `/playground` | `ComponentPlayground.vue` | Optional | 可后置，纯前端为主 |
| `/hooks` | `HooksView.vue` | No | 明确排除 |
| `/ssh` | `SshView.vue` | No | 明确排除 |

## Shared UI Modules

以下共享 UI / composable 建议整体迁移，而不是重写成第二套页面：

- `App.vue`
- `router/index.js`
- `components/Q*.vue`
- `components/NavItem.vue`
- `components/SkillDetailModal.vue`
- `components/SkillContextPanel.vue`
- `components/CommandPanel.vue`
- `components/FileTree.vue`
- `components/FilePreview.vue`
- `components/SkillImportModal.vue`
- `components/SubmoduleBadge.vue`
- `components/SkillSyncBadge.vue`
- `components/StatusBadge.vue`
- `composables/useData.js`
- `composables/useSyncBridge.js`
- `composables/useSkillDetail.js`
- `composables/useToast.js`
- `composables/useCommands.js`
- `composables/useContextPanel.js`
- `composables/useEventBus.js`

以下共享模块需要裁剪后迁移：

- `App.vue`
  - 删除 `/hooks`、`/ssh` 导航
  - 删除 `SshModeBanner`
- `useServerHealth.js`
  - 保留 `/api/health` 检查
  - 删除 `/dev/restart-server` 依赖，或改成 skillreg 的可选 server control API
- `useRemoteData.js`
  - 删除，纯 ssh 依赖
- `useSshHosts.js`
  - 删除，纯 ssh 依赖
- `views/SshView.vue`
  - 删除
- `components/HooksView.vue`
  - 删除

## API Matrix

### 1. Health

| API | agent-hub 用途 | skillreg 状态 | 动作 |
|---|---|---|---|
| `GET /api/health` | 健康检查、workspace 状态 | 已有 | 保留；字段尽量兼容 `status` + workspace 信息 |
| `POST /dev/restart-server` | 开发环境重启 server | 缺失 | 不必 1:1 迁移；可移除 UI，或增加可选 server-control API |

### 2. Skills

| API | agent-hub 用途 | skillreg 状态 | 动作 |
|---|---|---|---|
| `GET /api/skills` | 轻量 skills 列表 | 已有 | 对齐响应结构 |
| `GET /api/skills?full=1` | 扩展数据：relationships、submodules、repoNodes、gitLogs | 部分已有 | 补齐 `gitLogs` 及完整结构 |
| `GET /api/skills/refresh` | 刷新全量数据 | 已有 | 返回 full 结构 |
| `GET /api/skills/:id` | 详情 | 已有 | 对齐字段 |
| `GET /api/skills/:id/relationships` | 关系明细 | 已有 | 保持 |
| `GET /api/skills/:id/stats` | 基本统计 | 已有 | 保持 |
| `GET /api/skills/:id/tree` | 技能文件树 | 缺失 | 新增 |
| `GET /api/skills/:id/file?path=` | 技能文件内容 | 缺失 | 新增 |
| `GET /api/skills/:id/export` | 导出 zip | 缺失 | 新增 |

### 3. Sync

| API | agent-hub 用途 | skillreg 状态 | 动作 |
|---|---|---|---|
| `GET /api/sync/config` | 读取 sync 配置 | 缺失 | 新增 |
| `GET /api/sync/status` | 徽标 / 面板状态 | 缺失 | 新增 |
| `GET /api/sync/targets` | 目标列表 | 已有，但结构偏弱 | 对齐 `name/path/status` + project 语义 |
| `POST /api/sync/targets` | 增加目标 | 已有 | 保持 |
| `DELETE /api/sync/targets/:name` | 删除目标 | 已有 | 保持 |
| `PUT /api/sync/targets/:name/skills` | 更新目标技能白名单 | 仅 stub | 完整实现或明示简化模型 |
| `PUT /api/sync/targets/:name/rename` | 重命名目标 | 已有 | 保持 |
| `POST /api/sync/execute` | 执行同步 | 已有 | 保持 |
| `GET /api/sync/skill-presence?skill=` | 查询 skill 出现在什么 target | 缺失 | 新增 |
| `GET /api/sync/target-skills?target=` | 查询 target 中的 skill | 缺失 | 新增 |
| `GET /api/sync/diff?skill=&target=` | 查看 skill diff | 缺失 | 新增 |
| `POST /api/sync/remove-skill` | 从 target 删除 skill | 缺失 | 新增 |
| `GET /api/sync/target-file?skill=&target=&path=` | 读取 target 侧文件 | 缺失 | 新增 |
| `GET /api/sync/discover-home` | 自动发现 home 下 agent dirs | 已有 | 保持 |
| `GET /api/sync/discover?path=` | 自动发现指定路径 | 已有 | 保持 |

### 4. Projects

| API | agent-hub 用途 | skillreg 状态 | 动作 |
|---|---|---|---|
| `GET /api/sync/projects` | 项目组列表 | 已有 | 保持 |
| `POST /api/sync/projects` | 创建项目组 | 已有 | 保持 |
| `GET /api/sync/projects/:id` | 项目组详情 | 已有 | 保持 |
| `POST /api/sync/projects/:id/targets` | 新增目标 | 已有 | 保持 |
| `DELETE /api/sync/projects/:id/targets` | 删除目标 | 已有 | 保持 |
| `DELETE /api/sync/projects/:id` | 删除项目组 | 已有 | 保持 |

### 5. Submodules

| API | agent-hub 用途 | skillreg 状态 | 动作 |
|---|---|---|---|
| `GET /api/submodules` | 子模块列表与状态 | 已有 | 对齐状态字段 |
| `POST /api/submodules/sync-preview` | 同步预览 | 已有 | 保持 |
| `POST /api/submodules/diff` | dirty diff | 已有 | 保持 |
| `POST /api/submodules/sync` | 执行同步 | 缺失 | 新增 |
| `POST /api/submodules/refresh` | 刷新远程状态 | 缺失 | 新增 |
| `POST /api/submodules/fix-detached` | 修 detached head | 已有 | 保持 |

### 6. Files / Git / Import

| API | agent-hub 用途 | skillreg 状态 | 动作 |
|---|---|---|---|
| `GET /api/files/tree` | 通用文件树 | 已有 | 保持 |
| `GET /api/files/content` | 通用文件内容 | 已有 | 保持 |
| `GET /api/git/logs` | Git 历史 | 已有 | 对齐 full skills 响应中的嵌入方式 |
| `POST /api/import/workspace/create` | 创建 workspace | 已有 | 保持 |
| `POST /api/import/upload` | 上传 zip | 已有 | 保持 |
| `POST /api/import/validate` | 校验导入源 | 已有 | 保持 |
| `POST /api/import/execute` | 执行导入 | 已有 | 保持 |
| `POST /api/import/preview-update` | 预览更新 | 已有 | 保持 |
| `POST /api/import/execute-update` | 执行更新 | 已有 | 保持 |
| `POST /api/import/git-clone` | git clone 导入源 | 已有 | 保持 |
| `POST /api/import/git-import` | git 导入 | 已有 | 保持 |
| `POST /api/import/cleanup` | 清理临时目录 | 已有 | 保持 |

### 7. Compat Layer

旧前端中仍有一部分组件直接调用兼容路径，而不是统一 API client：

- `GET /api/skill-tree?skill=`
- `GET /api/skill-file?skill=&path=`
- `GET /api/skill-sync-targets`
- `POST /api/sync-skills`
- `GET /api/refresh-data`
- `GET /api/skill-target-file?skill=&target=&path=`
- `GET /api/skill-diff?skill=&target=`
- `GET /api/skill-target-presence?skill=`
- `GET /api/target-skills?target=`
- `POST /api/remove-skill-from-target`

建议：

- 第一阶段增加 `compat.py`，把这些旧路径映射到新 FastAPI 路由
- 第二阶段再统一前端，移除兼容层依赖

这样能把“后端补契约”和“前端迁 UI”两个风险拆开。

## Gap Summary

### P0: 必须先补的后端能力

- `/api/skills/:id/tree`
- `/api/skills/:id/file`
- `/api/skills/:id/export`
- `/api/sync/config`
- `/api/sync/status`
- `/api/sync/skill-presence`
- `/api/sync/target-skills`
- `/api/sync/diff`
- `/api/sync/remove-skill`
- `/api/sync/target-file`
- `/api/submodules/sync`
- `/api/submodules/refresh`
- compat routes

### P1: 迁移 Vue Dashboard 主体

- 迁移 `App.vue`、`router/`、核心页面与通用组件
- 删除 hook / ssh 路由与组件
- 保持现有设计语言，避免退化成临时 HTML 面板

### P2: 构建与托管

- `skillreg/dashboard` 改为 Vite/Vue 工程
- FastAPI 静态托管 `dashboard/dist`
- 增加 SPA fallback 支持 history 路由

### P3: 可选完善

- `ComponentPlayground.vue`
- server restart UX 替代方案
- 完整移除 compat layer

## Proposed Phases

### Phase 1: API freeze for dashboard migration

- 基于本矩阵冻结要支持的 endpoint 集
- 明确不支持 hooks / ssh / agent / kanban
- 为缺失 endpoint 写测试骨架

### Phase 2: FastAPI parity layer

- 补齐 `skills.py` 缺口
- 补齐 `sync.py` 缺口
- 补齐 `submodules.py` 缺口
- 新增 `compat.py`

### Phase 3: Vue dashboard import

- 将 `agent-hub/infra/dashboard/src` 迁入 `skillreg/dashboard/src`
- 删除 hooks / ssh 依赖
- 接通新的 FastAPI API

### Phase 4: Static serving + build integration

- Vite build 输出到 `dashboard/dist`
- FastAPI 托管构建产物
- 校验直达路由 `/skills`、`/sync`、`/repos` 等

### Phase 5: Real workspace verification

- 使用 `agent-hub-kex` 作为真实 workspace
- 验证 skill / sync / project / submodule / import / logs 全链路

## Suggested Implementation Order

1. 先补 FastAPI endpoint 和 compat layer
2. 再迁 Vue Dashboard 主壳与页面
3. 再接 build + static serving
4. 最后做真实 workspace 验证

## Acceptance Criteria

- `uv run pytest` 通过
- Dashboard 对应 API 有自动化测试覆盖关键响应结构
- Vue Dashboard 可从 `skillreg` 打开并正常使用
- 不出现 hooks / ssh 菜单、页面、调用
- 使用 `agent-hub-kex` 作为 workspace 时可完成：
  - skills 浏览
  - skill 文件预览
  - sync target 管理
  - project 管理
  - submodule 状态与 diff
  - git logs 查看
