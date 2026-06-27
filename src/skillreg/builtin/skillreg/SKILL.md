---
name: skillreg
description: skillreg — skill registry control plane. 用 dashboard 管理 skills, sync 到 agent targets, 浏览文件和 git 历史.
---

# skillreg

skillreg 是 agent skills 的中控平台，提供：

- **Dashboard** — 可视化管理面板，浏览/导入/同步 skills
- **CLI** — `skillreg config` / `skillreg dashboard open` / `skillreg workspace create`
- **Sync** — 将 workspace 中的 skills 同步到 Claude/CodeBuddy/Codex 等 agent 的 skills 目录

## 快速开始

```bash
uv tool install skillreg
skillreg workspace create ~/my-skills
skillreg dashboard open
```

## 架构

skillreg 采用双仓库模型：

- **skillreg** — 中控产品仓 (CLI + FastAPI + Dashboard)
- **workspace** — 用户 skills 存储仓 (skills/ + repos/)

详见 [skillreg-v2 PRD](https://github.com/fcraft/skillreg/blob/main/specs/skillreg-v2.md)。
