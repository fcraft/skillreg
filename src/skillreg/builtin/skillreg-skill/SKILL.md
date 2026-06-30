---
name: skillreg-skill
description: 当用户需要使用 skillreg 管理本地 AI Agent Skills 时使用，包括创建或切换 workspace、注册包含 SKILL.md 的本地目录、转换 skill、配置同步目标、执行同步、查看差异、打开 dashboard 或排查 skillreg 相关问题。
metadata:
  version: "1.4.1"
---

# skillreg-skill

当用户想用 `skillreg` 完成 skill 的注册、导入、转换、同步、查看状态或排障时，优先使用这个 skill。

核心心智模型：

- 用户关心的是“把本地已经写好的 skill 放进我的 skill workspace，并同步给 agent 用”。
- 用户不需要关心当前是在业务项目、skill 源码项目、`skillreg` 产品仓，还是 workspace 仓。
- agent 要负责识别本地 skill 来源、确认当前 `skillreg` workspace，然后完成注册或给出可执行的下一步。

## 触发场景

- 用户说"用 skillreg 管一下这个 skill"
- 用户说"注册这个 skill"、"把这个 skill 注册一下"、"把这个目录注册成 skill"
- 用户要把一个本地目录、zip、git 仓库注册进 workspace
- 用户要把 `skills/<name>` 转成 `repos/<name>-cli/skill/<name>`
- 用户要把 workspace 中的 skills 同步到 Claude、Codex、`.agents/skills` 等目标目录
- 用户反馈 `skillreg` 命令找不到、dashboard 起不来、workspace 不生效、sync 结果不对

## 先做什么

1. 识别要注册的 skill 来源：
   - 用户给了路径：优先用该路径。
   - 用户没给路径：从当前工作目录开始找 `SKILL.md`；如果当前目录本身就是 skill 目录，直接使用当前目录。
   - 如果找不到 `SKILL.md`，先告诉用户需要一个包含 `SKILL.md` 的目录，并说明当前检查过哪里。
2. 跑 `skillreg config`，确认当前 `workspace_path`、targets 和配置文件位置。
3. 如果 `workspace_path` 为空，先创建或引导选择 workspace；不要要求用户判断“产品仓/工作区仓”。
4. 如果命令不存在或环境没装好，读 `references/install.md`。
5. 如果命令能跑但行为异常（workspace 不对、dashboard/sync 出错），读 `references/troubleshooting.md`。

## 推荐工作流

### 1. 创建或确认 workspace

| 场景 | 操作 |
|------|------|
| 新建 workspace | `skillreg workspace create ~/my-skills` |
| 查看当前 workspace | `skillreg workspace current` |
| 切换已有 workspace | `skillreg workspace switch /path/to/workspace` |
| 需要图形操作 | `skillreg dashboard open` 或 `skillreg dashboard start` |

说明：
- workspace 只需要包含 `skills/` 目录；用户不需要理解产品仓和 workspace 仓的区别。
- CLI 适合 agent 从任意项目完成注册、同步、状态确认；dashboard 适合人类批量管理和查看细节。

### 2. 把本地 skill 纳入 workspace

根据用户目标选择入口：

| 目标 | 入口 |
|------|------|
| 把当前目录或给定路径里的 skill 注册进 workspace | `skillreg register <path>` |
| 覆盖同名 skill | `skillreg register <path> --force` |
| 注册时改名 | `skillreg register <path> --name <name>` |
| 查看 workspace skills | `skillreg list` |
| 把 file skill 变成 repo/CLI 骨架 | `skillreg convert <name>` |

要点：
- `register` → 把 skill 放进 `skills/<name>/`
- `convert` → 把 `skills/<name>` 迁到 `repos/<name>-cli/skill/<name>/`，并生成基础 CLI repo 骨架
- “注册”默认不是注册当前代码仓库本身，而是注册其中包含 `SKILL.md` 的 skill 目录。
- 如果用户在任意业务项目里说“注册 skill”，agent 应主动定位该项目中的 `SKILL.md` 或询问具体 skill 目录。

### 3. 同步到 agent 目标目录

常用 CLI：

```bash
skillreg target add ~/.codex/skills
skillreg target list
skillreg sync status
skillreg sync execute --target ~/.codex/skills
skillreg sync execute --target ~/.codex/skills --skill my-skill
skillreg diff my-skill --target ~/.codex/skills
```

项目组同步：

```bash
skillreg project create --name my-project --target ~/.codex/skills --target ~/.claude/skills
skillreg sync execute --project my-project
```

状态含义（不要混淆）：

| 状态 | 含义 |
|------|------|
| `synced` | workspace 和 target 一致 |
| `modified` | target 里有本地改动或差异 |
| `missing` | 配置里有这个 skill，但目标缺失 |

## agent 行为约束

- **先验证再行动**：先用 `skillreg config`、dashboard、API 或测试确认能力真的可用。
- **用户心智优先**：不要把"产品仓 / workspace 仓 / submodule 仓"作为用户必须回答的问题；这些只是 agent 内部判断路径和命令时的实现细节。
- **任意项目可触发**：用户可能在任何项目里说"注册 skill"。先找本地 `SKILL.md`，再把它注册进 `skillreg config` 指向的 workspace。
- **优先工具**：如果用户只是要完成一项实际操作，优先直接用 `skillreg` 完成，不要手工复制目录。
- **排障先诊断**：如果用户是在排障，先给出现状和根因，再决定是否需要改代码或改配置。

## 何时读参考文档

| 问题类型 | 参考文档 |
|----------|----------|
| 安装、开发态启动、PATH/venv 问题 | `references/install.md` |
| dashboard 起不来、workspace 不对、sync 异常、skill 没注入、命令行为不符合预期 | `references/troubleshooting.md` |
