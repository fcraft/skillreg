# skillreg 排障指南

当用户反馈“装好了但不能用”“workspace 不对”“sync 看起来不可信”“dashboard 起不来”时，按这个顺序排查。

## 1. 先看当前配置

第一步永远先跑：

```bash
skillreg config
```

重点看：

- 配置文件是不是 `~/.skillreg/config.json`
- `workspace_path` 有没有值
- 指向的路径是不是用户真正想操作的那个 workspace

如果 `workspace_path` 为空或错误，很多问题都会是表象。

## 2. workspace 问题

典型现象：

- skills 列表为空
- dashboard 里看不到预期 skill
- sync 用的是错误仓库

检查：

```bash
ls <workspace>
ls <workspace>/skills
```

确认：

- workspace 路径存在
- 它是目录，不是文件
- 至少包含 `skills/`

如果用户已经有 workspace，但 CLI 当前没指向它：

```bash
skillreg workspace switch <workspace>
skillreg workspace current
```

如果更适合人类确认，也可以打开 dashboard 后在 header 中切换。

## 3. dashboard 起不来

先区分是“命令起不来”，还是“服务起来了但页面打不开”。

### 命令起不来

优先检查：

```bash
which skillreg
skillreg config
```

如果 `skillreg` 不存在，回到 `install.md` 重新安装。

### 服务起来但网页打不开

可直接用开发命令确认后端是否可起：

```bash
python -m uvicorn skillreg.server:app --host 127.0.0.1 --port 8787
```

再检查：

- 端口是否被占用
- `dashboard/dist` 是否存在
- 浏览器访问的是不是正确端口

## 4. register / convert 异常

### register 失败

优先检查源目录：

- 是否存在 `SKILL.md`
- frontmatter 里是否有 `name`
- `name` 是否满足 `[A-Za-z0-9][A-Za-z0-9_-]*`

常见冲突：

- `skills/<name>` 已存在
- 没有传 `--force`

推荐命令：

```bash
skillreg register <path>
skillreg register <path> --force
skillreg register <path> --name <new-name>
```

### convert 失败

优先检查：

- `skills/<name>/SKILL.md` 是否存在
- `repos/<name>-cli` 是否已经存在

语义上要记住：

- `convert` 是迁移，不是复制
- 成功后原来的 `skills/<name>` 会移入 `repos/<name>-cli/skill/<name>/`

## 5. sync 状态不对

先别急着改代码，先确认状态解释有没有搞错：

- `synced`：一致
- `modified`：目标侧有差异
- `missing`：配置/期望存在，但目标缺失

如果用户说“怎么全是 missing / not-installed”，先检查：

- 当前 target 路径是不是对的
- target 目录是否真的存在
- workspace 当前选中的 skill 是否在目标里出现

推荐命令：

```bash
skillreg target list
skillreg sync status
skillreg sync execute --target <target> --dry-run
skillreg sync execute --target <target>
skillreg diff <skill> --target <target>
```

如果 target 没配置：

```bash
skillreg target add <target>
```

## 6. builtin skill 没注入

`skillreg` 会把 builtin `skillreg-skill` 注入到：

```text
<workspace>/.skillreg/builtin/skillreg-skill/
```

如果用户说看不到：

1. 先确认当前 workspace 是对的
2. 再检查这个目录是否存在
3. 如果是开发态，确认源码里 `src/skillreg/builtin/skillreg-skill/` 存在
4. 如果是安装态，确认 wheel 中包含 builtin 目录

## 7. 什么时候该改代码

只有在下面这些都确认之后，再进入代码修复：

- 配置路径正确
- workspace 正确
- 输入目录和 skill 元数据合法
- target 路径和目标状态核对过
- CLI 安装和 PATH 没问题

也就是说，先排除“环境 / 配置 / 路径 / 术语理解”问题，再动实现。
