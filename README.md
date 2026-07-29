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

- **CLI**：创建/切换 workspace，注册/转换 skill，管理 NPM 来源、targets/projects，执行 sync，查看 diff，启动 dashboard。
- **Skill**：内置 `skillreg-skill`，让 agent 在任意项目里识别本地 `SKILL.md` 并注册到当前 workspace。
- **Dashboard**：提供图形入口，可从本地、ZIP、Git 或 NPM 包导入 skill，管理 NPM 来源、同步目标、项目组、仓库状态、依赖图与 Git 记录。

## 安装与使用

使用 uv 安装：

```bash
uv tool install skillreg
```

也可以通过 npm 安装：

```bash
npm install --global skillreg
```

npm 启动器会运行完全相同版本的 Python 包。系统有 `uv` 时直接使用；否则首次
运行时会通过 Python 3.9+ 创建隔离环境，并从 PyPI 下载依赖。

安装后：

```bash
skillreg workspace create ~/my-skills
skillreg register /path/to/my-skill
skillreg target add ~/.codex/skills
skillreg sync execute --target ~/.codex/skills
skillreg dashboard open
```

查看完整命令和参数：

```bash
skillreg -h
skillreg <group> -h
```

需要导入 NPM Skill 包时，使用 `skillreg source npm -h` 查看来源预览、导入
和更新命令。skillreg 只下载并校验 registry 制品，不执行 `npm install` 或
生命周期脚本。

## 开发

```bash
git clone https://github.com/fcraft/skillreg.git
cd skillreg
uv sync --extra dev
scripts/install-git-hooks.sh
uv run pytest -q
uv run --with ruff ruff check src/ tests/ scripts/
```

本地发版使用：

```bash
scripts/release.sh
```

脚本会校验版本、创建并推送 tag，再由 GitHub Actions 发布到 GitHub Release、
PyPI 和 npm。

## Contributors

![Contributors](https://contrib.rocks/image?repo=fcraft/skillreg)

## Trend

[![Star History Chart](https://api.star-history.com/svg?repos=fcraft/skillreg&type=Date)](https://www.star-history.com/#fcraft/skillreg&Date)

## License

[MIT](LICENSE)
