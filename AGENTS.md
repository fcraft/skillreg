# AGENTS.md

## 项目定位

`skillreg` 是一个本地 skill registry control plane：

- 本体就是 Python CLI
- 后端是 FastAPI
- 前端是 dashboard
- 管理对象是一个独立的 workspace（`skills/` + `repos/`）

这个仓不再以 `agent-hub` 为运行时依赖，也不再维护 `skillreg-cli` / `ui-framework` 之类的并列子模块结构。

## 当前真实边界

已经可用：

- workspace 创建
- workspace 切换
- skill 扫描
- import（本地/zip/git）
- sync target 管理与同步
- submodule 状态查看与只读远程检查
- files / git logs / dashboard 主体

已经补齐：

- `/api/registry/register`
- `/api/registry/convert`

但发布前仍要继续校验：

- registry 接口与 dashboard/CLI 的语义是否完全一致
- convert 后的 repo 模板是否足够支撑真实用户继续开发

## 代码组织约定

- `src/skillreg/cli.py`
  - CLI 入口
- `src/skillreg/server/`
  - API routes
- `src/skillreg/services/`
  - 业务逻辑
- `dashboard/src/`
  - 前端页面、组件、composables
- `src/skillreg/builtin/skillreg-skill/`
  - skillreg 自身注入到 workspace 的 builtin skill

## 开发规范

### 1. 保持 workspace 模型清晰

所有能力都围绕“当前配置的单个 workspace”展开。

除非明确要做多 workspace 管理，否则不要提前引入：

- workspace profile 集
- 隐式候选仓库列表
- 复杂的跨 workspace 缓存

### 2. 文档要反映真实状态

- 不要保留失效的迁移期描述在主入口文档里
- 迁移实施记录放 `docs/archive/`
- 面向用户的入口文档保持简洁、准确

### 3. 对 sync 语义保持谨慎

Sync 相关状态必须区分清楚：

- `synced`
- `modified`
- `missing`
- `not-installed`

不要让前端展示语义和后端状态语义漂移。

### 4. 对外发布视角优先

凡是 README、CLI、Dashboard header、错误提示等用户直接可见的内容，都优先考虑：

- 陌生用户能不能理解
- 本地安装后能不能直接使用
- 不依赖作者口头解释

### 5. 测试要求

改动后优先做：

- 单文件 pytest
- dashboard build

涉及接口契约、workspace、sync、submodule 时，优先补测试。

## 对 agent 的要求

当 agent 修改本仓时：

1. 先确认当前实现是否真的支持某项能力，再写文档或 UI 文案
2. 不要把 archive 文档当成当前事实来源
3. 如果发现结构性占位目录、迁移残留或文档失效，应主动收口
4. 如果用户说“发布前整理”，优先做减法，不要继续扩张 scope
