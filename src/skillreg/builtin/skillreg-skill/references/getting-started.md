# skillreg 新手引导

这个文档用于第一次使用 skillreg，目标是完成一条最小但完整的闭环：

1. 准备本地 Skill Workspace
2. 导入第一个 Skill
3. 配置 Agent 同步目标
4. 确认本地 Git 记录与远端备份边界

## 先理解 Workspace

Workspace 是 skillreg 管理 Skill 的本地目录，通常包含：

- `skills/`：直接注册的独立 Skill
- `repos/`：转换为子仓或 CLI 骨架后的 Skill

用户不需要理解产品仓或历史 daemon 工作流，只需要决定这个本地目录放在哪里

推荐默认位置：

```text
~/my-skills
```

## 路径一：使用 Dashboard

运行：

```bash
skillreg dashboard open
```

首次打开且尚未配置 Workspace 时，Dashboard 会显示首次设置页：

1. 选择“创建新的”或“使用已有的”
2. 填写本地路径
3. 创建完成后查看 Workspace 路径和初始提交
4. 继续导入首个 Skill
5. 前往 Sync 工具添加同步目标

Dashboard 创建 Workspace 时会自动初始化 Git 并创建首个提交，但不会配置远端或执行 push

如果在顶部切换 Workspace 时输入的路径尚不存在，Dashboard 会先展示创建确认。只有用户确认后，才会在该路径执行同一套 Workspace 初始化流程

## 路径二：使用 CLI

先查看当前状态：

```bash
skillreg config
```

如果显示 `workspace : (未配置)`，创建新的 Workspace：

```bash
skillreg workspace create ~/my-skills
skillreg workspace current
```

创建命令会自动完成：

- 创建 `skills/` 和 `repos/`
- 初始化本地 Git 仓库
- 创建 `chore: init skillreg workspace` 初始提交
- 把当前 Workspace 指针写入 `~/.skillreg/config.json`

如果已经有符合结构的目录，直接切换：

```bash
skillreg workspace switch /path/to/workspace
```

已有 Workspace 至少需要包含 `skills/` 目录

## 导入第一个 Skill

本地目录需要包含 `SKILL.md`

```bash
skillreg register /path/to/my-skill
skillreg list
```

注册成功后，skillreg 会把内容复制到 `skills/<name>/`，并只提交这次注册涉及的路径

也可以在 Dashboard 的 Skill 列表中点击“导入”，选择本地目录、ZIP、Git 或 NPM 来源

## 配置第一个同步目标

以 Codex 为例：

```bash
skillreg target add ~/.codex/skills
skillreg sync status
skillreg sync execute --target ~/.codex/skills
```

其他常见目标：

```text
~/.agents/skills
~/.claude/skills
```

添加目标不会自动同步，先查看状态，再执行 sync

## 本地提交与远端备份

skillreg 会为 Workspace 中受管内容创建本地 Git 提交，默认使用：

```text
skillreg <skillreg@example.invalid>
```

这意味着变更已经有本地历史，但还没有远端备份

如果用户希望备份到已有 Git 仓库，需要由用户提供 remote 地址，再执行：

```bash
cd ~/my-skills
git remote add origin <remote-url>
git push -u origin HEAD
```

不要替用户猜测 remote，不要声称创建 Workspace 后已经上传远端

## 完成检查

完成首次设置后，应能确认：

- `skillreg config` 显示正确的 `workspace_path`
- Workspace 中存在 `skills/`、`repos/` 和 `.git/`
- `git log -1` 能看到初始提交或最近一次 Skill 提交
- `skillreg list` 能看到已导入的 Skill
- `skillreg target list` 能看到至少一个同步目标
- `skillreg sync status` 能返回实际同步状态

## Agent 行为建议

当用户说“初始化 skillreg”或“第一次怎么用”时：

1. 先运行 `skillreg config`，不要假设 Workspace 已配置
2. 未配置时优先说明默认路径 `~/my-skills`，然后创建或引导用户在 Dashboard 创建
3. 创建后明确说明首个提交已经生成，但没有 remote、没有 push
4. 如果当前目录包含 `SKILL.md`，继续完成首次注册
5. 根据用户正在使用的 Agent 添加对应 target，再检查和执行同步
6. 最后用上面的完成检查给出实际结果，不只复述命令

如果命令不存在或安装失败，转到 `install.md`

如果 Workspace、Git 或 sync 状态异常，转到 `troubleshooting.md`
