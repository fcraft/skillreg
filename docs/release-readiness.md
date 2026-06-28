# skillreg 发布准备度

本文档基于当前仓库状态，回答两个问题：

1. 现在离“真正可发布”还有多远？
2. 发布前最值得补的是什么？

## 当前判断

`skillreg` 已经具备明确产品雏形，可以持续内部使用，也已经接近一个可演示、可邀请少量外部用户试用的版本。

但如果目标是：

- 公开 GitHub 仓库
- 让陌生用户按 README 直接装起来
- 遇到问题时能自助定位
- 不需要作者本人在场解释

那还**不建议立刻正式发布**。

## 发布阻断项

这些项建议在正式发布前补齐。

### 1. 安装链路还不完整

README 里写的是：

`uv tool install skillreg`

但当前仓库状态更像“本地开发可运行”，不是已经完成发布到公开包源的成品。

至少需要明确：

- 发布目标是 PyPI、GitHub Release，还是源码安装
- `uv tool install skillreg` 最终从哪里装
- dashboard 静态资源是否随 wheel/sdist 正确打包

如果 wheel 里没有稳定包含 dashboard 构建产物，用户安装后 `dashboard open` 体验会不完整。

### 2. Dashboard 打包/分发策略还不够明确

当前仓库里 dashboard 是独立前端工程，开发时可 build，可由 Python 托管。

但正式发布前需要确认：

- wheel/sdist 是否总是包含 `dashboard/dist`
- 没有前端构建环境的用户，安装后能否直接使用 dashboard
- CI 是否校验“打包后的安装产物”真的能启动 dashboard

### 3. 真实用户场景文档还不够闭环

现在 README 已经能说明基本能力，但发布前还缺至少一篇更接近用户任务的文档：

- 如何接入一个已有 skills 仓库
- 如何新增 sync target
- Sync 页里 `未安装 / missing / modified` 各自是什么意思
- submodule 页面里的 `ahead / behind / diverged / dirty` 怎么理解

如果没有这层说明，第一次使用门槛会偏高。

### 4. 当前项目还有明显“迁移后残留味道”

虽然主工作面已经清爽很多，但 repo 里仍然能看出它刚从 agent-hub 迁过来：

- 归档区里仍保留大量 agent-hub 迁移语境文档
- registry 已经迁到主仓，但 dashboard / CLI / 文档 对“导入、注册、转换”三种术语的表达还可以继续统一

这些不一定要马上删，但发布前至少要决定：

- 它们是长期保留结构，还是短期过渡
- 如果保留，README 里要明确这是 roadmap/占位，不是用户需要操作的部分

## 建议在发布前完善

这些不是硬阻断，但补上会显著提升发布质量。

### 1. workspace 管理再顺一点

当前已经支持单个 workspace 切换，这是好的最小闭环。

建议补：

- 最近使用的 workspace 列表
- 切换前的基本校验反馈
- 未配置 workspace 时更明确的空态指引

### 2. Sync 语义说明与 UI 统一

最近已经修了一轮 Sync 页的目标展示和 missing 分组问题。

发布前建议再统一：

- `missing`
- `未安装`
- `modified`
- `synced`

在单 target 视图、项目组视图、diff 视图中的文案语义，避免用户误解。

### 3. CLI 命令面仍偏薄

当前 CLI 只有：

- `skillreg config`
- `skillreg dashboard open`
- `skillreg workspace create`

对正式发布来说有点太轻。

建议至少补其中一类：

- `skillreg workspace switch <path>`
- `skillreg target list/add/remove`
- `skillreg doctor`

尤其 `doctor` 很适合发布版。

### 4. 需要一个“发布前 smoke test”

建议 CI 或本地发布流程里加一条真正的冒烟：

1. 新建临时 venv
2. 安装构建产物
3. 创建 workspace
4. 启动 dashboard
5. 调 `/api/health`、`/api/skills`

这样可以提前发现“本地开发能跑，打包后不能跑”的问题。

## 可以后置

这些可以放到 `v0.x` 或 `v1.x` 继续做，不必阻塞首发。

- 多 workspace 管理器
- 更丰富的 workspace 发现能力
- SSH/远程同步
- UI 框架抽离
- 品牌/视觉统一升级
- 更完整的导入来源管理

## 对当前文档整理的建议

建议保留：

- `README.md`
- `docs/project-layout.md`
- `docs/release-readiness.md`

建议归档：

- `docs/archive/dashboard-migration-matrix.md`
- `docs/archive/issues/`

建议后续考虑进一步瘦身：

- 归档中的迁移文档可继续减少外链引用
- 把“导入”“注册”“转换”的术语和入口在 README、dashboard、CLI 中进一步统一

## 一句话结论

现在的 `skillreg` 已经是一个**可持续开发、可内部使用、可演示**的项目；距离“陌生用户拿来就能顺畅上手的正式发布版”，还差一轮**安装分发闭环 + 使用文档闭环 + 发布冒烟闭环**。
