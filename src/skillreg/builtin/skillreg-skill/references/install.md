# skillreg 安装与启动

这个文档给 agent 一个稳定起点：当用户要“安装 skillreg”“把 skillreg CLI 跑起来”“确认本地环境能不能用”时，先按这里走。

## 1. 先确认本机入口

无论用户当前在哪个项目里，都先用下面两个命令识别 `skillreg` 是否可用、当前 workspace 指向哪里：

```bash
pwd
skillreg config
```

如果 `skillreg` 命令不存在，再继续看下面的安装方式。

不要要求用户先判断自己是在“产品仓”还是“workspace 仓”。用户通常只是在某个本地项目里想把一个包含 `SKILL.md` 的目录注册进 workspace。

## 2. 面向用户的 CLI 安装

如果目标是给本机装一个可直接调用的 `skillreg`，优先建议：

```bash
uv tool install skillreg
```

安装后先确认：

```bash
skillreg config
which skillreg
```

如果项目还没真正发布到公开包源，`uv tool install skillreg` 可能失败。这种情况下要明确告诉用户：

- 当前更可靠的是源码开发态安装
- 或者从本地仓库执行 `uv pip install -e .`

## 3. 开发态安装

当 agent 正在 `skillreg` 仓库里改代码时，优先用开发态安装：

```bash
uv venv
uv pip install -e ".[dev]"
```

安装后可验证：

```bash
skillreg config
skillreg dashboard open --no-browser
```

如果用户是在当前仓库里直接联调，也可以直接起服务：

```bash
python -m uvicorn skillreg.server:app --host 127.0.0.1 --port 28787
```

## 4. 初始化最小可用闭环

安装完成后，最小验证顺序：

```bash
skillreg workspace create ~/my-skills
skillreg workspace current
```

然后确认：

- `~/.skillreg/config.json` 已生成
- `workspace_path` 指向新建 workspace
- workspace 下至少有 `skills/` 和 `repos/`

## 5. 注册和同步闭环

如果当前目录或用户给定目录包含 `SKILL.md`：

```bash
skillreg register .
skillreg list
skillreg target add ~/.codex/skills
skillreg sync status
skillreg sync execute --target ~/.codex/skills
```

如果同名 skill 已存在：

```bash
skillreg register . --force
```

如果需要把 `skills/<name>` 转成 CLI 子仓骨架：

```bash
skillreg convert <name>
```

## 6. 常用命令

```bash
skillreg config
skillreg workspace create <path>
skillreg workspace current
skillreg workspace switch <path>
skillreg register <path>
skillreg list
skillreg target list
skillreg target add <path>
skillreg sync status
skillreg sync execute --target <path>
skillreg diff <skill> --target <path>
skillreg dashboard open
skillreg dashboard start
skillreg dashboard status
skillreg dashboard stop
skillreg dashboard open --no-browser
```

当前 agent 应该把 CLI 看成：

- `config / workspace current`：确认配置和当前 workspace
- `register / list / convert`：完成 skill 纳入 workspace 的闭环
- `target / sync / diff / project`：完成同步和状态确认
- `dashboard open`：进入人类可视化管理入口
