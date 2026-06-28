# dashboard 构建产物打通 + v1 闭环验证

## What to build

把 dashboard 从 dev server 模式切换为**构建产物**模式，由 Python 后端 StaticFiles 托管；`skillreg dashboard open` 打开的是构建好的前端 + 后端，而非 dev server。然后跑通 v1 完整闭环。

**构建产物打通**：
- dashboard（Vue）构建成静态文件（`dist/`），Python 后端用 `StaticFiles` 托管。
- `skillreg dashboard open` 启动后端 + 打开浏览器指向构建产物。
- `CommandPanel`（348 行，跨域命令聚合）适配新后端，确认其调用的 API 范围都已迁完。

**v1 闭环验证**（PRD 5.1）：空 workspace → 创建 workspace → 自动出 self-skill → 从 git/zip/本地导入 skill → 浏览文件 → 看 git 历史 → sync 到 targets。端到端 demo。

**收尾清理**：
- 移除/隐藏 `SshModeBanner`（ssh 是 v1.x，v1 不含）。
- `ComponentPlayground`（453 行，组件演示页）保留供开发，不进发布构建。

## Acceptance criteria

- [ ] dashboard 构建成静态文件，Python 后端 StaticFiles 托管
- [ ] `skillreg dashboard open` 打开构建产物（非 dev server），无需 Node
- [ ] CommandPanel 跨域命令可用
- [ ] v1 闭环端到端跑通：空 workspace → 创建 → self-skill 自动出现 → 导入 skill → 浏览 → 看 git 历史 → sync 到 `~/.claude/skills`
- [ ] SshModeBanner 在 v1 移除/隐藏
- [ ] ComponentPlayground 不进发布构建
- [ ] `uv tool install skillreg` + `skillreg dashboard open` 全流程无需 Node

## Blocked by

- #3（sync/registry/skills）
- #4（workspace/self-skill/import）
- #5（files/git/submodules/hooks）
