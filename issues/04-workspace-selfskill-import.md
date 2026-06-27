# workspace 创建 + self-skill 注入 + import 全能力

## What to build

打通"把 skill 弄进 workspace"的完整纵切：创建空 workspace → self-skill 自动注入 → 从外部来源导入 skill → 更新已有 skill。

**workspace 创建**：
- dashboard / CLI 提供"创建 workspace"：选本地位置 → `git init` → 生成骨架（**强制 `skills/` 目录存在**、可预置 `.gitattributes`、README）→ 写入 `~/.skillreg/config.json` 的 workspace 指针。
- workspace 骨架只含 `skills/` + `repos/` + `.gitignore`（含 `.skillreg/builtin/`）+ README，**不含 `infra/`、不含 `sync-skills.json`**（PRD 2.3）。

**self-skill 注入**：
- self-skill submodule 的 SKILL.md 打进 Python 包（`importlib.resources` 读取）。
- skillreg 启动时更新到 workspace 的 `.skillreg/builtin/skillreg/`（**保留区，gitignore，不进 workspace git**）。
- 确保 `.skillreg` 不在 scan exclude 列表，scan 复用通用扫描逻辑（零特例链路，PRD 2.4）。

**import 全能力**（迁 `infra/server/services/importer.js` ~520 行到 Python）：
- 三种来源：zip 上传解压、git-clone 到 temp、本地目录
- 两种模式：复制成 `skills/<name>/`（skill 模式）、作为 submodule 添加到 `repos/`（submodule 模式）
- update 流程：preview + execute 更新已有 skill
- import 目标基准切到 workspace 路径

**前端适配**：复制 `SkillImportModal`（1265 行）+ `ProjectManager` 相关，改 `api/index.js` 适配。

来源代码：`infra/server/services/importer.js`、`infra/server/routes/import.js`、`infra/dashboard/src/components/SkillImportModal.vue`。

## Acceptance criteria

- [ ] dashboard / CLI 能创建 workspace（git init + 强制 `skills/` + `.gitattributes` + README），指针自动写入配置
- [ ] workspace 骨架不含 infra/ 和 sync-skills.json，`.gitignore` 含 `.skillreg/builtin/`
- [ ] self-skill 打进 Python 包，启动时注入到 workspace `.skillreg/builtin/skillreg/`
- [ ] self-skill 不进 workspace git，scan 能扫到（`.skillreg` 不在 exclude 列表）
- [ ] 从 git URL 导入 skill（skill 模式）到 workspace，scan 能扫到
- [ ] 从本地目录导入 skill（skill 模式）
- [ ] zip 上传导入 skill
- [ ] 作为 submodule 添加到 `repos/`（submodule 模式）
- [ ] 已有 skill 的 update 流程（preview + execute）可用
- [ ] dashboard SkillImportModal 适配新后端

## Blocked by

- #1（API 契约）
- #2（仓骨架 + Python 后端框架，需 self-skill submodule 占位）
