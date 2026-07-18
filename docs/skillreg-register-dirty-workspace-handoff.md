# `skillreg register` 在脏 workspace 中误提交既有暂存内容：交接

记录日期：2026-07-14

## 结论

`skillreg register` 在目标 workspace 已有暂存内容时，会把本次注册路径之外的 index 一并提交。一次实际注册已经复现该行为。

该问题已于 2026-07-19 在产品仓修复：workspace 自动提交现在使用显式 pathspec，只提交本次操作涉及的路径，并保留用户原有的 index、worktree 和未跟踪文件。注册、导入、删除、重命名和 submodule 相关调用点已统一收紧。

## 实际事件

执行环境的当前 workspace 是 `/Users/kex/Code/project_kex/agent-hub-kex`。注册源为临时目录中的 `k-commit-working-tree` Skill，命令为等价的：

```bash
skillreg register <local-skill-directory>
```

注册成功后，skillreg 自动创建：

```text
4561bf77529b3a65a5df50fb50150b384d0108ea
skillreg: register 'k-commit-working-tree'
```

该 commit 本应只包含：

- `skills/k-commit-working-tree/SKILL.md`
- `skills/k-commit-working-tree/agents/openai.yaml`

实际还提交了注册前存在的 README 改动，以及整个 `skills/tpm-skill/` 的删除（包括引用文档和平台二进制）。commit 作者/提交者为 `skillreg <skillreg@example.invalid>`。

注册的 Skill 已同步并验证为 `synced`：

- `/Users/kex/.agents/skills`
- `/Users/kex/.codebuddy/skills`
- `/Users/kex/.claude/skills`
- `/Users/kex/.workbuddy/skills`

它本身结构有效，workspace 源码位于 `agent-hub-kex/skills/k-commit-working-tree/`。

## 根因

`src/skillreg/services/importer.py` 的 `_git_add_commit()`（约 893–906 行）先运行：

```python
git add <注册路径>
```

但随后运行不带 pathspec 的：

```python
git commit -m <message>
```

Git 会提交整个 index，而不是只提交刚刚 `git add` 的路径。因此任何预先暂存的文件都会被带入注册 commit。

相同帮助函数也被导入、删除 Skill、添加 submodule 等流程复用，修复必须评估这些调用点。

## 当前 workspace 状态

事件后仍保留的既有工作区状态包括：

```text
 M .skillreg/builtin/skillreg-skill/SKILL.md
 m repos/ntcompose-adb-debug
?? skills/to-prompt/
```

注册前 README 同时存在 index 与 worktree 修改（`MM README.md`）。自动提交后，原始 staged/unstaged hunk 边界不应假定仍可无损恢复。

## 处理约束

- 未经用户明确确认，不要 `reset --hard`、强推或删除任何 Skill。
- 不要再次在该脏 workspace 运行 `skillreg register`、`remove`、`import`、`rename` 等会自动提交的操作。
- 处理当前 `4561bf7` 前，先创建备份 ref，并导出当前 `git status`、`git diff HEAD^..HEAD` 和 index/worktree diff。
- 恢复的目标是：保留 `k-commit-working-tree`，将 README 与 `tpm-skill` 变化重新交给用户决定；精确复原原 staged hunk 可能需要检查 dangling blob 或让用户确认。

## 建议修复

1. 让 `_git_add_commit()` 只提交显式路径，例如使用 `git commit --only -m <message> -- <paths>`；或使用隔离的 `GIT_INDEX_FILE`，避免读取/改写用户现有 index。
2. 在自动注册前检测已有 staged 改动。首选策略是明确拒绝并提示用户清理或确认，而不是静默混入提交。
3. 将 Git 命令从字符串拆分改为 pathspec 参数列表，正确处理空格与特殊字符。
4. 为 CLI 与服务层各加入回归测试：workspace 预先暂存无关文件，注册一个 Skill 后断言新 commit 仅包含 `skills/<name>/`；无关 index 和 worktree 内容均保持不变。
5. 评估所有 `_git_add_commit()` 调用点，确保 import/remove/submodule 等操作同样不会吞入脏 index。

## 后续恢复方案（需用户确认后执行）

最直接的语义恢复是：先为 `4561bf7` 建立备份 ref，再回到其父提交，将其全部内容恢复为工作区改动，仅重新暂存并提交 `skills/k-commit-working-tree/`。这会保留文件内容，但可能无法自动恢复 README 原有的 staged/unstaged hunk 划分。

若用户希望保留 `tpm-skill` 删除或 README 改动，应先拆分其真实意图，再决定是否保留当前 commit、重写为多个 commit，或仅做后续补充提交。

## 验收

修复后至少验证：

```bash
uv run pytest -q
uv run --with ruff ruff check src/ tests/ scripts/
uv run skillreg register -h
```

并在隔离的 Git fixture 中构造“已有 staged README + 未跟踪临时文件 + 新 Skill”场景，断言注册 commit 不包含 README 或临时文件。
