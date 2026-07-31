# Dashboard 单 Skill 变更提交方案

## 1. 背景与目标

当前 Dashboard 可以查看 workspace 中的 skill、文件、同步差异和 Git 提交记录，也能在注册、导入、删除等流程中自动创建限定路径的提交，但缺少一个面向已有 skill 的闭环：

1. 查看某个 skill 相对当前 Git HEAD 的未提交变更
2. 预览将被提交的文件和内容
3. 输入提交信息
4. 只提交该 skill，不带入 workspace 中其他路径的改动
5. 提交后得到明确结果并刷新 Dashboard 状态

本方案中的“单 Skill 提交”指：提交当前 workspace 内某个 skill 目录下的全部工作树变更。首期不提供文件勾选、部分行提交、amend 或 push。

核心验收标准：

> workspace 同时存在多个 staged、unstaged 和 untracked 变更时，用户可以预览并提交一个独立 skill，最终 commit 只包含该 skill，其他路径的工作树和暂存状态保持不变

## 2. 当前仓库能力盘点

### 2.1 可以直接复用的能力

| 能力 | 现有位置 | 可复用方式 |
| --- | --- | --- |
| 获取当前 workspace | `src/skillreg/config.py`、各 server route 的 workspace helper | 继续以 `~/.skillreg/config.json` 指向的 workspace 为唯一操作根目录 |
| 查找 skill | `services/skill_registry.py::get_skill` | 根据 `skill_id` 获取规范化的 skill 元数据，不允许前端传入任意磁盘路径 |
| Skill 相对路径 | registry 返回的 `path` | 作为 Git pathspec 的来源，例如 `skills/demo-skill` |
| 仓库归属信息 | registry 返回的 `isSubmodule`、`submodulePath` | 区分主 workspace skill 和 repo/submodule 内 skill |
| 限定路径提交 | `services/importer.py::_git_add_commit` | 复用 `git add -A -- <pathspec>` 和 `git commit --only ... -- <pathspec>` 的核心思路，不直接复用当前实现 |
| 隔离提交测试基础 | `tests/test_importer.py`、`tests/test_cli_commands.py` | 已证明注册 skill 时可以保留其他路径的 staged、unstaged 和 untracked 修改 |
| Git 历史接口 | `server/git.py::git_logs` | 提交成功后沿用现有 Git logs 数据结构和刷新机制 |
| 子模块状态和 diff | `server/submodules.py` | 复用仓库归属、porcelain 状态和子模块指针相关经验，不复用 shell 字符串执行方式 |
| Skill 详情入口 | `dashboard/src/components/SkillDetailModal.vue` | 增加「版本变更」页签 |
| 弹窗、按钮、通知 | `QModal`、`QButton`、`useToast` | 复用现有交互基础组件 |
| 文本 diff | `QDiffViewer.vue`、前端 `diff` 依赖 | 泛化文案后复用 old/new 内容对比能力 |
| 全局数据刷新 | `composables/useData.js::refresh` | 提交成功后刷新 skill registry、submodule 状态和 Git logs |

### 2.2 不能直接复用或需要优化的部分

#### `_git_add_commit` 不能作为 Dashboard 执行服务直接复用

当前 helper 会捕获并忽略全部 `CalledProcessError`，调用方无法区分：

- 没有内容可提交
- Git identity 未配置
- hook 拒绝提交
- pathspec 错误
- 仓库或 index 异常
- Git 命令超时

Dashboard 必须返回确定的成功或失败结果，因此应把核心逻辑抽到新的 Git service，原有 importer 再按需要迁移调用。

#### `server/submodules.py` 的状态解析和命令执行只适合作为参考

现有实现使用 `git status --porcelain` 的文本正则和带 `shell=True` 的字符串命令，面对空格、引号、rename 双路径等情况不够稳健。新能力应统一使用参数数组，并解析 NUL 分隔输出：

```text
git status --porcelain=v2 -z --untracked-files=all -- <pathspec>
```

#### `QDiffViewer` 的语义需要泛化

当前组件固定使用“仓库/目标”作为两侧含义，适合 skill 同步，不适合 Git 的“HEAD/工作区”。建议新增可选属性：

- `oldLabel`
- `newLabel`
- `oldContent`
- `newContent`

保留旧属性兼容现有同步页面，或抽出更通用的 `QTextDiffViewer`，由同步和 Git 预览共同使用。

#### 现有错误响应格式不完全统一

前端 API client 优先读取 `data.error`，FastAPI 常规 `HTTPException` 默认返回 `detail`。新接口应统一返回结构化错误，前端 client 同时兼容 `error` 和 `detail`，避免只显示 HTTP 状态文本。

## 3. 范围与仓库语义

### 3.1 首期范围

首期支持 registry 中 `isSubmodule == false` 的 skill，典型路径为：

```text
skills/<skill-name>/**
```

提交发生在当前 workspace 主仓库，pathspec 取 registry 返回的完整 `path`，不能通过 skill 名自行拼接目录。

首期支持：

- tracked 文件修改
- staged 和 unstaged 修改
- untracked 文件
- 文件删除
- Git 可识别的 rename
- 文本文件 old/new diff
- 二进制或超大文件的状态预览
- 并发变更阻止
- 保留 skill 外部的工作树和暂存区

首期不支持：

- 文件级选择提交
- 部分行提交
- amend
- push
- merge/rebase 冲突处理
- repo/submodule 内 skill 的执行提交

### 3.2 Repo/submodule skill

registry 已能识别 `isSubmodule` 和 `submodulePath`。这类 skill 的真实 Git 仓库是 `workspace/<submodulePath>`，不能把内部文件作为主仓库普通 pathspec 提交。

首期 UI 仍可展示其仓库归属，但执行按钮禁用并说明：

> 此 Skill 属于独立仓库，当前请在仓库管理中提交

后续扩展应复用同一 Git service 的“仓库上下文”抽象：

1. 在子仓库中提交该 skill 相对路径
2. 提交成功后提示主 workspace 的 gitlink 已变化
3. 用户单独预览并决定是否提交主仓库指针

不建议一次点击自动生成子仓库和主仓库两个 commit，这会隐藏两层版本语义，也会让失败恢复复杂化。

## 4. 推荐架构

新增：

```text
src/skillreg/services/git_manager.py
```

职责：

- 校验 workspace 是 Git worktree
- 根据 registry skill 解析仓库根和安全 pathspec
- 读取 HEAD、状态和变更文件
- 生成预览令牌
- 读取单文件 HEAD/工作树内容
- 执行限定 pathspec 的隔离提交
- 对 Git 错误进行分类
- 在失败时恢复本次操作对 index 造成的副作用

`server/git.py` 只负责：

- Pydantic 请求和响应模型
- HTTP 状态码映射
- 调用 `git_manager`

不要继续把可复用 Git 业务逻辑写进 route，也不要让前端控制仓库路径或 pathspec。

建议的内部模型：

```text
SkillGitContext
├── workspace_root
├── repository_root
├── skill_id
├── skill_path
├── repository_relative_path
├── repository_kind: workspace | submodule
└── head
```

即使首期只开放 `workspace` 类型，也先建立这个边界，避免后续支持 repo skill 时重写接口。

## 5. 后端接口

### 5.1 获取单 Skill 变更预览

```http
GET /api/git/skills/{skill_id}/changes
```

建议响应：

```json
{
  "skill": "demo-skill",
  "repository": {
    "kind": "workspace",
    "path": "."
  },
  "skillPath": "skills/demo-skill",
  "head": "5b5ccf4a20b9...",
  "previewToken": "sha256:...",
  "hasChanges": true,
  "committable": true,
  "blockedReason": null,
  "files": [
    {
      "path": "SKILL.md",
      "workspacePath": "skills/demo-skill/SKILL.md",
      "status": "modified",
      "indexStatus": "modified",
      "worktreeStatus": "modified",
      "binary": false
    }
  ],
  "summary": {
    "added": 0,
    "modified": 1,
    "deleted": 0,
    "renamed": 0
  }
}
```

`indexStatus` 和 `worktreeStatus` 用于准确表达 staged/unstaged 情况，但首期提交仍包含整个 skill 的最终工作树状态。

状态值限定为：

- `added`
- `modified`
- `deleted`
- `renamed`
- `type-changed`
- `unmerged`

若出现 `unmerged`，返回预览但设置 `committable: false`，避免 Dashboard 代替用户解决冲突。

### 5.2 获取单文件 diff 内容

```http
GET /api/git/skills/{skill_id}/diff?path=SKILL.md&preview_token=sha256%3A...
```

建议响应：

```json
{
  "path": "SKILL.md",
  "status": "modified",
  "binary": false,
  "tooLarge": false,
  "oldContent": "HEAD 中的内容",
  "newContent": "当前工作区内容"
}
```

约束：

- `path` 必须是 skill 目录内的相对路径
- resolve 后必须仍位于 skill 根目录内
- symlink 不得借此读取 skill 外文件
- 单侧内容超过既有文件预览上限时返回 `tooLarge: true`
- 二进制文件不返回正文
- deleted 文件的 `newContent` 为空
- untracked 文件的 `oldContent` 为空

这里展示的是 `HEAD → 当前工作区`，与“提交整个 skill 最终状态”的语义一致，不拆成 staged diff 和 unstaged diff。

### 5.3 执行提交

```http
POST /api/git/skills/{skill_id}/commit
```

请求：

```json
{
  "message": "chore: update demo-skill",
  "previewToken": "sha256:..."
}
```

成功响应：

```json
{
  "success": true,
  "commit": "7ad8e4c...",
  "shortCommit": "7ad8e4c",
  "message": "chore: update demo-skill",
  "files": [
    "skills/demo-skill/SKILL.md"
  ]
}
```

推荐状态码：

| 状态码 | 场景 |
| --- | --- |
| 400 | workspace 未配置、不是 Git 仓库、提交信息非法 |
| 404 | skill 不存在 |
| 409 | 预览令牌失效、存在冲突、没有可提交内容 |
| 422 | skill 类型当前不可提交 |
| 500 | Git identity、index、文件系统或 Git 执行失败 |

错误体建议统一为：

```json
{
  "error": {
    "code": "preview_stale",
    "message": "Skill 变更已发生变化，请重新预览"
  }
}
```

同时优化 Dashboard API client，使其能从字符串或对象形式的 `error/detail` 中提取用户可见信息。

## 6. 预览一致性与并发控制

只传 `expectedHead` 不够：HEAD 未变化时，skill 文件仍可能在预览后被编辑。

因此使用不透明的 `previewToken`，至少绑定：

- repository root 标识
- 完整 HEAD hash
- skill pathspec
- porcelain v2 状态记录
- tracked 文件相对 HEAD 的 diff 内容摘要
- untracked 文件的路径、类型、大小和内容摘要

生成方式可以是对规范化数据做 SHA-256。执行提交时，在同一临界区内重新计算 token；不一致则返回 `409 preview_stale`，不执行 `git add`。

这样能够保证“用户提交的就是刚才预览的内容”，也能覆盖：

- HEAD 被其他进程推进
- 文件内容被编辑
- 新增或删除文件
- symlink 目标或文件类型改变

## 7. 隔离提交算法

推荐流程：

1. 获取进程内 workspace Git 操作锁
2. 重新解析 skill，确认路径和仓库归属未变化
3. 校验当前预览令牌
4. 确认不存在 unmerged 文件
5. 备份当前 Git index 内容和元数据
6. 执行 `git add -A -- <skill-pathspec>`，纳入新增、修改和删除
7. 执行限定 pathspec 的 commit
8. 读取新 commit 的文件列表并做断言
9. 清理 registry cache
10. 返回 commit 信息

限定提交继续采用 Git 原生语义：

```text
git commit --only -m <message> -- <skill-pathspec>
```

它比自行构造 tree、`commit-tree` 和 `update-ref` 更合适，因为 Git 会负责更新 HEAD 和协调真实 index；手工更新 HEAD 容易让原有暂存区仍基于旧 HEAD，产生难以理解的 staged 差异。

异常处理：

- `git add` 或 `git commit` 失败时，恢复操作前的 index
- 不修改工作树文件
- 保留 stderr，并映射为结构化错误
- 不允许像现有 `_git_add_commit` 一样吞掉异常

实现时应使用参数数组和 `subprocess.run(..., shell=False)`，为状态、diff 和 commit 分别设置合理 timeout。

### 7.1 Git hooks 的处理

通用 Git hook 可以任意修改工作树或 index，因此“运行任意用户 hook”和“严格保证其他路径完全不变”无法同时无条件成立。

推荐首期对 Dashboard 的单 skill 隔离提交使用：

```text
git commit --only --no-verify ...
```

理由：

- 该操作的核心承诺是严格限定提交范围并保留其他状态
- 当前项目的 `commit-msg` hook 会修改并暂存版本文件，明显超出选中 skill 的路径
- Dashboard 已经可以在提交前完成非空 message、变更冲突和路径安全校验

UI 在提交确认处明确显示“为保证单 Skill 隔离，本次提交不运行本地 Git hooks”。首期不提供开关，避免用户开启后误以为仍有严格隔离保证。

若未来需要运行 hooks，应设计为独立高级模式，并在执行前快照工作树和 index、执行后检测副作用；不能只在 commit 产生后检查文件列表，因为那时已经无法安全地把操作当作未发生。

### 7.2 进程并发边界

服务内使用按 repository root 维度的锁，防止两个 Dashboard 请求同时操作 index。它不能阻止外部 Git 进程，因此仍需要：

- Git 自身的 `index.lock`
- `previewToken` 的提交前复核
- Git 失败后的清晰提示

## 8. Dashboard 交互方案

### 8.1 入口

在 `SkillDetailModal` 增加第四个页签：

```text
详情 | 安装 | 同步状态 | 版本变更
```

切换到「版本变更」时懒加载当前 skill 的 Git 预览。不要在 skill 列表加载时为每个 skill 查询 Git 状态，避免 N+1 Git 调用。

### 8.2 页面状态

页面至少覆盖：

1. 加载中
2. 无变更
3. 有可提交变更
4. 存在冲突，不可提交
5. repo/submodule skill，暂不支持执行
6. workspace 不是 Git 仓库
7. 预览或提交失败
8. 提交成功

有变更时展示：

- 仓库归属和 skill 路径
- 新增、修改、删除、重命名统计
- 文件列表及 staged/unstaged 标识
- 点击文件后的 diff
- 提交信息输入框
- 「重新检查」和「提交更新」按钮

建议提交信息占位提示：

```text
chore: update <skill-name>
```

不自动写入输入框，用户必须明确确认 message。校验首行非空，并设置合理长度上限。

### 8.3 提交确认

点击「提交更新」后显示二次确认：

- skill 名称
- 变更文件数量
- commit message
- 不运行本地 Git hooks 的说明
- 不会提交或清理其他 workspace 修改的说明

提交期间禁用重复操作。

若返回 `preview_stale`：

1. 保留用户输入的提交信息
2. 自动重新加载变更
3. 提示“文件已变化，请确认最新预览后再次提交”

提交成功后：

1. 显示短 commit hash
2. 清空提交信息
3. 重新加载当前页签，状态应为无变更
4. 调用 `useData().refresh()` 刷新全局 Git logs 和 registry 数据
5. 不自动 push

## 9. 前端拆分建议

避免继续膨胀已有的 `SkillDetailModal.vue`，新增：

```text
dashboard/src/components/SkillGitChanges.vue
dashboard/src/components/SkillGitCommitConfirm.vue
dashboard/src/composables/useSkillGitChanges.js
```

职责：

- `SkillGitChanges`：状态、文件列表、diff 和提交区
- `SkillGitCommitConfirm`：提交确认弹窗
- `useSkillGitChanges`：加载、选择文件、提交、stale refresh 状态机

`SkillDetailModal` 仅负责传入 skill 和控制页签。

API client 新增：

```text
fetchSkillGitChanges(skillId)
fetchSkillGitDiff(skillId, path, previewToken)
commitSkillChanges(skillId, message, previewToken)
```

## 10. 测试方案

### 10.1 Git service 单元测试

必须覆盖：

1. 解析 modified、added、deleted、renamed、type-changed
2. 同时返回 staged 和 unstaged 状态
3. untracked 文件进入预览和提交
4. ignored 文件不进入预览
5. 文本文件返回 HEAD/工作区内容
6. deleted 和 untracked 文件的单侧内容为空
7. 二进制、超大文件不返回正文
8. diff 路径 `..` 越界被拒绝
9. symlink 不能读取 skill 外文件
10. preview token 在 HEAD 或文件变化后失效
11. 无变化不产生空 commit
12. unmerged 状态禁止提交
13. commit 只包含 skill pathspec
14. 保留 skill 外 staged 修改
15. 保留 skill 外 unstaged 修改
16. 保留 skill 外 untracked 文件
17. skill 自身 staged 与 unstaged 的最终工作区内容全部提交
18. Git add/commit 失败后恢复原 index
19. Git identity 缺失返回明确错误
20. hook 不被执行

### 10.2 API 测试

在 `tests/test_files_git.py` 或新的 `tests/test_skill_git.py` 中覆盖：

- workspace 未配置
- 非 Git workspace
- skill 不存在
- 主仓 skill 正常 preview/diff/commit
- repo/submodule skill 返回不可提交
- stale token 返回 409
- 结构化错误格式
- 成功响应包含实际 commit 文件列表

### 10.3 Dashboard 测试

覆盖：

- 页签懒加载
- 无变更空状态
- 文件列表和 diff 切换
- 冲突与 submodule 禁用态
- commit message 校验
- 二次确认
- 防止重复提交
- stale 后保留 message 并刷新
- 成功后刷新 Git logs
- API 错误文案正确展示

建议补一条 Dashboard E2E：准备包含两个 dirty skill 和一个额外 staged 文件的临时 workspace，通过 UI 提交其中一个 skill，然后从 Git commit 和 status 两侧验证隔离性。

## 11. 实施顺序

### 阶段一：后端只读预览

1. 新建 `git_manager.py` 和仓库上下文模型
2. 使用 porcelain v2 `-z` 实现单 skill 状态解析
3. 实现 preview token
4. 实现安全的单文件 old/new 内容接口
5. 完成 service 和 API 测试

阶段验收：可以通过 API 准确预览主仓独立 skill 的全部最终提交内容，没有写操作。

### 阶段二：隔离提交

1. 实现 repository 级进程锁
2. 实现 token 复核
3. 实现 index 备份、限定 pathspec 提交和失败恢复
4. 使用 `--no-verify` 保证隔离语义
5. 返回实际 commit 文件列表和结构化错误
6. 补齐 dirty workspace、失败恢复和并发测试

阶段验收：任意其他路径处于 staged、unstaged、untracked 状态时，单 skill commit 均不消费或清理它们。

### 阶段三：Dashboard 闭环

1. 泛化 diff viewer
2. 增加 `useSkillGitChanges`
3. 增加版本变更页签和确认弹窗
4. 实现 stale refresh、toast 和全局数据刷新
5. 完成前端测试与 E2E

阶段验收：用户可以在一个 skill 详情中完成预览、确认、提交和结果核对。

### 阶段四：Repo/submodule 扩展

1. 开放 repository context 的 submodule 类型
2. 在子仓库中限定 skill 相对路径提交
3. 展示主仓 gitlink 后续动作
4. 与现有 SubmoduleStatus 流程整合

阶段验收：两层提交保持显式、可分别预览和执行，不自动 push。

## 12. 验证门禁

实现完成后至少执行：

```bash
uv run python scripts/check_version.py
uv run pytest -q
uv run --with ruff ruff check src/ tests/ scripts/
```

涉及 Dashboard 时额外执行其构建和测试命令。若最终增加 CLI 对等入口，再补充：

```bash
uv run skillreg -h
uv run skillreg <新增命令组> -h
```

## 13. 最终决策摘要

- 入口放在单 skill 详情的「版本变更」页签
- 首期只执行提交主 workspace 中的独立 skill
- registry 是 skill 路径和仓库归属的唯一事实来源
- 抽取独立 `git_manager`，不直接复用会吞错误的 importer helper
- 使用 porcelain v2 NUL 输出和参数数组，不新增 Git Python 依赖
- 预览令牌绑定 HEAD 与 skill 实际内容，避免预览后内容漂移
- 使用 Git 原生 `commit --only`，不自行构造 commit tree
- 失败时恢复 index，其他工作树内容不变
- 首期使用 `--no-verify`，明确保证单 skill 隔离语义
- 提交和 push 分离
- submodule skill 后续采用显式两阶段流程
