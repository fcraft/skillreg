# 开源发布 + agent-hub-kex 迁移 + 旧仓归档

## What to build

skillreg v1 开源发布的收尾工作：文档、CI、真实迁移验证、旧仓归档。

**开源发布物料**：
- `README.md`：skillreg 定位、安装（`uv tool install skillreg`）、快速开始（创建 workspace → 导入 skill → sync）、架构说明（双仓库模型）、链接到 `specs/skillreg-v2.md` PRD。
- `LICENSE`：选定开源协议（建议 MIT 或 Apache-2.0，与开源定位匹配）。
- `.github/workflows/ci.yml`：GitHub Actions CI（Python lint/test、dashboard build、可选 `uv tool install` 冒烟）。

**agent-hub-kex 迁移验证**（PRD 5.5）：
- 把 agent-hub-kex（`/Users/kex/Code/project_kex/agent-hub-kex`）的 `skills/` + `repos/` 内容搬进一个新的 workspace 仓库。
- 安装 skillreg，配置 `~/.skillreg/config.json` 指向该 workspace。
- 验证全链路：扫描、sync、dashboard 展示。
- 此迁移与 skillreg 仓 git 历史无关，是独立工作项。

**旧仓归档**（PRD 5.3，A1 决策）：
- 新仓 v1 跑通 + agent-hub-kex 迁移完成后，旧 agent-hub 仓（`git@git.woa.com:kexjhhuang/agent-hub.git`）归档。
- 不双轨共存。

## Acceptance criteria

- [ ] README.md 完整，含安装、快速开始、架构说明
- [ ] LICENSE 已选定并添加
- [ ] GitHub Actions CI 配置完成，PR/push 触发 lint/test/build
- [ ] agent-hub-kex 的 skills/+repos/ 迁移到新 workspace 仓库成功
- [ ] skillreg + 新 workspace 全链路验证通过（扫描/sync/dashboard）
- [ ] 旧 agent-hub 仓归档（archived），无双轨共存
- [ ] `fcraft/skillreg` 公开仓可被第三方 clone + `uv tool install` + `dashboard open` 使用

## Blocked by

- #6（v1 闭环验证）
