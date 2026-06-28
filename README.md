<!--lint disable awesome-heading awesome-github awesome-toc double-link -->

<h2 align="center">skillreg</h2>

<p align="center">
本地 AI Agent Skill 管理工具
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

`skillreg` 用来管理本地 AI Agent Skills。你可以把任意项目里写好的
`SKILL.md` 注册到统一 workspace，再同步到 Claude、Codex、CodeBuddy 或
`~/.agents/skills` 等 agent skill 目录。

## 能力

- **CLI**：创建/切换 workspace，注册/转换 skill，管理 targets/projects，执行 sync，查看 diff，启动 dashboard。
- **Skill**：内置 `skillreg-skill`，让 agent 在任意项目里识别本地 `SKILL.md` 并注册到当前 workspace。
- **Dashboard**：提供图形入口，可导入 skill、切换 workspace、管理同步目标、查看 Diff、按项目组批量同步、查看仓库状态/依赖图/Git 记录。

## 安装与使用

```bash
uv tool install skillreg
skillreg workspace create ~/my-skills
skillreg register /path/to/my-skill
skillreg target add ~/.codex/skills
skillreg sync execute --target ~/.codex/skills
skillreg dashboard open
```

Dashboard 默认打开：

```text
http://127.0.0.1:8787
```

常用命令：

```bash
skillreg config
skillreg workspace create <path>
skillreg workspace current
skillreg workspace switch <path>
skillreg register <path> [--force] [--name name]
skillreg list
skillreg convert <name>
skillreg target list
skillreg target add <path>
skillreg sync status
skillreg sync execute --target <path> [--skill name]
skillreg project create --name <name> --target <path>
skillreg sync execute --project <name>
skillreg diff <skill> --target <path>
skillreg submodule list
skillreg dashboard start
skillreg dashboard status
skillreg dashboard stop
skillreg dashboard open --no-browser
```

## 开发

```bash
git clone https://github.com/fcraft/skillreg.git
cd skillreg
uv sync --extra dev
uv run pytest -q
uv run --with ruff ruff check src/ tests/ scripts/
```

## Contributors

![Contributors](https://contrib.rocks/image?repo=fcraft/skillreg)

## Trend

[![Star History Chart](https://api.star-history.com/svg?repos=fcraft/skillreg&type=Date)](https://www.star-history.com/#fcraft/skillreg&Date)

## License

[MIT](LICENSE)
