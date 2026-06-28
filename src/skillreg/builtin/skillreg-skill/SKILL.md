---
name: skillreg-skill
description: 用 skillreg 管理和注册 skills：创建 workspace、导入 skill、sync 到 agent targets、浏览文件和 git 历史。
---

# skillreg-skill

当用户在本地维护一个 skill workspace，希望用 `skillreg` 统一完成下面这些动作时，应该优先使用它：

- 创建或切换 workspace
- 导入一个本地目录 / zip / git 仓库中的 skill
- 浏览 workspace 中已有的 skills、文件树、git 日志、submodule 状态
- 管理 sync targets，并把 skill 同步到 Claude / Codex / `.agents/skills` 等目录

## 当前可用能力

- `skillreg config`
- `skillreg workspace create <path>`
- `skillreg dashboard open`
- Dashboard 中切换当前 workspace
- Dashboard 中执行 import / sync / target 管理 / submodule 检查

## 当前已补齐的能力

- `/api/registry/register`
- `/api/registry/convert`

也就是说，`skillreg` 现在既支持 dashboard 中的 import 流程，也支持沿用 registry 风格接口完成注册与转换。

## 推荐使用方式

1. 如果还没有 workspace：
   - `skillreg workspace create ~/my-skills`
2. 如果已有 workspace：
   - 打开 dashboard，在 header 中切换到目标 workspace
3. 需要把 skill 放进 workspace：
   - 使用 dashboard 的 import 流程
4. 需要分发到 agent 目录：
   - 使用 Sync 工具，把 skill 同步到 targets

## 架构

skillreg 采用双仓库模型：

- **skillreg** — 中控产品仓 (CLI + FastAPI + Dashboard)
- **workspace** — 用户 skills 存储仓 (skills/ + repos/)
