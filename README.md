<!--lint disable awesome-heading awesome-github awesome-toc double-link -->

<h2 align="center">skillreg</h2>

<p align="center">
本地 AI Agent Skill 管理中控
</p>

<p align="center">
<a href="docs/README.en.md">English</a>
</p>

<p align="center">
<img src="https://img.shields.io/badge/Python-teal?logo=python&logoColor=white&style=flat-square&color=3776ab" alt="Python">
<img src="https://img.shields.io/badge/FastAPI-teal?logo=fastapi&logoColor=white&style=flat-square&color=009688" alt="FastAPI">
<img src="https://img.shields.io/badge/Vue.js-teal?logo=vue.js&logoColor=white&style=flat-square&color=46b882" alt="Vue.js">
<img src="https://img.shields.io/badge/Vite-teal?logo=vite&logoColor=white&style=flat-square&color=646cff" alt="Vite">
</p>

<p align="center">
<img src="https://img.shields.io/github/actions/workflow/status/fcraft/skillreg/ci.yml?style=flat-square&color=ffeab4" alt="CI">
<img src="https://img.shields.io/github/v/release/fcraft/skillreg?include_prereleases&style=flat-square&color=8bd5ca" alt="Release">
<img src="https://img.shields.io/github/stars/fcraft/skillreg?logo=github&style=flat-square&color=f59688" alt="Stars">
<img src="https://img.shields.io/github/license/fcraft/skillreg?style=flat-square&color=ea3a59" alt="License">
</p>

## 这个项目是做什么的

`skillreg` 用来管理你本机上的 AI Agent Skills。

当你或 agent 在任意项目里写好一个包含 `SKILL.md` 的 skill 后，`skillreg`
可以把它注册到统一的 skill workspace，再同步到 Claude、Codex、CodeBuddy、
`~/.agents/skills` 等 agent skill 目录。

你不需要关心“产品仓”“workspace 仓”这些内部概念。日常使用时只需要记住：

- 本地有一个写好的 `SKILL.md`
- 用 `skillreg` 把它收进 workspace
- 再同步给需要使用它的 agent

## Dashboard 能做什么

Dashboard 是 `skillreg` 的主要操作入口，适合日常管理和排查：

- **Skill 列表**：查看所有 skill，按类型筛选，打开详情，导入本地 skill
- **Sync 工具**：管理同步目标，发现 `~/` 下的 agent skill 目录，安装、同步、卸载、查看 Diff
- **项目组**：把多个 target 编成项目组，按项目批量安装或同步
- **仓库状态**：查看 submodule / repo 状态，检查远程状态，处理仓库同步问题
- **依赖关系图**：查看 skill、仓库和依赖关系
- **提交记录**：查看 workspace 和仓库的 Git 提交历史
- **命令面板**：通过 `Cmd/Ctrl + K` 快速跳转页面、刷新数据、定位 skill
- **Workspace 切换**：在页面顶部直接切换当前管理的 workspace
- **组件实验室**：浏览 Dashboard 基础 UI 组件状态，方便继续开发

## 快速开始

```bash
uv tool install skillreg
skillreg workspace create ~/my-skills
skillreg dashboard open
```

默认打开：

```text
http://127.0.0.1:8787
```

## 常用命令

```bash
skillreg config
skillreg workspace create <path>
skillreg dashboard open
skillreg dashboard open --no-browser
```

`skillreg config` 和 dashboard 启动命令会输出当前 workspace，方便 agent 或用户快速确认当前操作对象。

## Workspace 结构

```text
<workspace>/
├── skills/                  # 单个目录型 skills
├── repos/                   # repo / CLI 型 skills
└── .skillreg/builtin/       # skillreg 内置 skill
```

本机配置文件：

```text
~/.skillreg/config.json
```

## 开发

```bash
git clone https://github.com/fcraft/skillreg.git
cd skillreg
uv venv
uv pip install -e ".[dev]"
uv pip install ruff build
python scripts/check_version.py
python -m pytest -q
ruff check src/ tests/ scripts/
```

## 发版

发版流程见 [docs/release-process.md](docs/release-process.md)。版本号以
`pyproject.toml` 为源头，并由 CI 校验 `__version__`、Git tag 和构建产物一致。

## Contributors

![Contributors](https://contrib.rocks/image?repo=fcraft/skillreg)

## Trend

[![Star History Chart](https://api.star-history.com/svg?repos=fcraft/skillreg&type=Date)](https://www.star-history.com/#fcraft/skillreg&Date)

## License

[MIT](LICENSE)
