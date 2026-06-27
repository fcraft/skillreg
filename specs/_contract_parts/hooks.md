# hooks 域 API 契约

> 现状逆向（只读源码沉淀）。`hook-manager.js` 是 subprocess 壳，通过 `python3 infra/hooks.py --json <cmd>` 转发；`hooks.py` 用 `@hook-*` 注解发现 hook 脚本，写 `~/.claude/settings.json`（`--local` 写项目级 `.claude/settings.json`）。

## Endpoints

### `GET /api/hooks/scan` — 扫描可用的 hook 脚本（发现，不含安装态）
- 请求：无 query / 无 body
- 响应（`hooks.py` scan 子命令 `--json` 分支，hook-manager.js:31 `scanHooks()`）：
  - `native`: array — 来源 `hooks/` 的 hook 列表
  - `repos`: array — 来源 `repos/<name>/hooks/` 的 hook 列表
  - 每个 hook 元素字段（`parse_hook_metadata` 产出 + `scan_hooks` 补充）：
    - `id`: string — hook 标识；缺省取 `script_path.stem`（hooks.py:93-94）
    - `event`: string — 默认 `"PreToolUse"`（hooks.py:96）
    - `matcher`: string — 默认 `"Bash"`（hooks.py:97）
    - `timeout`: string — 默认 `"5000"`（hooks.py:98，注解值为字符串，install 时 `int()` 转）
    - `description`: string — 来自 `@hook-description` 注解（可有可无）
    - `script_path`: string — 脚本绝对路径（hooks.py:99）
    - `source`: string — `"hooks/"` 或 `"repos/<name>"`（hooks.py:122/141）
    - `path`: string — 相对 project_root 的路径（hooks.py:123/142）
- 错误：500 `{ error: <err.message> }`（routes/hooks.js:18）

### `GET /api/hooks/status` — 完整状态：可用 + 安装态 + 第三方
- 请求：query `local=1`（可选，切换到项目级 `.claude/settings.json`）
- 响应（`hooks.py` status 子命令 `--json` 分支，hooks.py:464-473）：
  - `hooks`: array — 全部扫描到的 hook（含安装态），每个元素 = scan 字段 + `installed`: bool
  - `available`: object — `agent_hub`: array（source ∈ `("hooks/", "global")`）、`repos`: array（source 以 `repos/` 开头）
  - `installed`: array — `installed===true` 的 hook 子集
  - `thirdParty`: array — 第三方 hook，元素字段：`source`: string（`"ping-island"`/`"task-notify"`/`"context-mode"`/`"GSD"`/`"unknown"` 分类）、`event`: string、`matcher`: string、`command`: string（hooks.py:300-305）
  - `third_party`: array — 同 `thirdParty`，legacy key（hooks.py:472，注释 "legacy key for tests"）
  - 额外行为：全局安装的绝对路径 hook（`python3 /abs/path`，脚本存在且 `@hook-` 注解有效）即使 scan 未命中也会被识别为 agent-hub 管理，`source="global"`、`installed=true`（hooks.py:329-347）
- 错误：500 `{ error: <err.message> }`（routes/hooks.js:29）

### `GET /api/hooks` — `/status` 的别名
- 请求：query `local=1`（可选）
- 响应：同 `GET /api/hooks/status`
- 错误：500 `{ error: <err.message> }`（routes/hooks.js:40）

### `POST /api/hooks/install` — 安装一个 hook（写入 settings.json）
- 请求：body JSON `{ id: string, local?: boolean }`（routes/hooks.js:47，`local` 默认 `false`）
  - **现状契约缺口**：dashboard `installHook()` 实际发送 `{ hookId, local, dryRun }`（api/index.js:303），字段名 `hookId` ≠ 后端读取的 `id` → 后端 `if (!id)` 命中 → 返回 400 `{ error: 'id is required' }`。前端 install 当前不可用。`dryRun` 后端路由层未消费（hooks.py 支持 `--dry-run` 但路由未透传）。
- 响应（hooks.py:209-226 `install_hook`）：
  - 已安装（跳过）：`{ success: true, hook: <id>, message: "Hook '<id>' 已安装，跳过", skipped: true }`
  - 新装成功：`{ success: true, hook: <id>, message: "已安装 hook: <id>", command: <cmd> }`
  - 未找到 hook id（CLI 层 exit 1）：`{ success: false, error: "未找到 hook: <id>" }`（hooks.py:517）
- 错误：400 `{ error: 'id is required' }`（缺 id）；500 `{ error: <err.message> }`（routes/hooks.js:52）
- 安装写入格式（hooks.py:195-218）：`settings.hooks[event]` 追加 `{ matcher, hooks: [{ type: "command", command, timeout }] }`；全局用绝对路径 `python3 <abs>`，本地用相对路径 `python3 <rel>`

### `POST /api/hooks/uninstall` — 卸载一个 hook（从 settings.json 移除）
- 请求：body JSON `{ id: string, local?: boolean }`（routes/hooks.js:59）
  - **现状契约缺口**：同 install，前端发送 `{ hookId, local, dryRun }`（api/index.js:307），`hookId` ≠ `id` → 400。
- 响应（hooks.py:237-262 `uninstall_hook`）：
  - 未安装：`{ success: true, hook: <id>, message: "Hook '<id>' 未安装", not_found: true }`
  - 卸载成功：`{ success: true, hook: <id>, message: "已卸载 hook: <id>" }`
  - 未找到 hook id（CLI 层 exit 1）：`{ success: false, error: "未找到 hook: <id>" }`（hooks.py:555）
- 错误：400 `{ error: 'id is required' }`；500 `{ error: <err.message> }`（routes/hooks.js:64）
- 清理行为：移除 hook 后若 entry.hooks 空 → 删 entry；event 列表空 → 删 event；hooks 段空 → 删 `hooks` 键（hooks.py:250-255）

### `POST /api/hooks/validate` — 校验已安装 hook 脚本是否存在
- 请求：无 body（routes/hooks.js:70 `validateHooks()` → hook-manager.js:57 `runHooksCli('validate')`）
- 响应：**现状契约缺口** — hooks.py validate 分支（hooks.py:565-589）始终输出纯文本（`  ✅ <cmd>` / `❌ 脚本不存在: <path>` / 汇总行），未实现 `--json` 输出；`runHooksCli` 强制 `JSON.parse(stdout)` 必然失败 → reject → 路由 catch → 500。即此 endpoint 经 HTTP 层恒定返回错误。
- 错误：500 `{ error: "Failed to parse hooks.py output: ..." }`（routes/hooks.js:74，经 hook-manager.js:23-25 reject）
- 另：dashboard `validateHooks()` 用 `GET /api/hooks/validate`（api/index.js:311），与后端 `POST` 方法不匹配 → Hono 不匹配该路由。

## 高危契约（按域适用）
- registry/skills 域必填：getAll() 返回 {skills, repoNodes, submodules, relationships, generatedAt}；skill 对象字段(id/name/description/type/graphType/parentNode/path/skillFilePath/fileCount/remoteUrl/parentSkill/isSubmodule/submodulePath)；repoNodes 字段(含 isSubmoduleRoot/branch)；graphType 四态(isolated-skill/cli-skill/repo-skill/repo-cli)及 skill/ 子路径判定；syncState 七态(synced/ahead/behind/diverged/dirty/missing/unknown)；submodule 指针 indexRef/indexAhead/indexBehind/indexDirty(indexDirty 不得砍);ntdev DEBUG 残留位置(skill-registry.js:508-510 须清除);classifySkillType(CLI vs Reference，向上找 pyproject.toml/src/*.py)。
- sync 域必填：三套 target 解析逻辑差异——resolveTargetArg(sync-manager.js:192，named 否则 raw)、_resolve_target_by_name_or_path(sync-skills.py:675，"看起来像路径"启发式)、resolve_targets_for_sync(sync-skills.py:709，只 named+agent-dir 自动发现+fallback)；统一目标显式三态 named/raw-path/agent-dir。config CRUD(getConfig/addTarget/removeTarget/renameTarget/updateTargetSkills)、project 注册表(~/.skillreg/projects.json)、discoverAgentDirs/discoverHomeAgentDirs。
- hooks 域：hook-manager.js 是 subprocess 壳(转发 hooks.py)，scan/status/install/uninstall/validate；hooks.py 用 @hook-* 注解发现，写 ~/.claude/settings.json(--local 写项目级)。
- import 域：三来源(zip upload/git-clone --depth 1/本地目录)×两模式(skill 复制到 skills/<name>/、submodule add 到 repos/)+update(preview/execute)；registerSkill 内部 git add/commit；isValidSkillName 正则 [A-Za-z0-9][A-Za-z0-9_-]*。
- files 域：buildTree(深度4/节点上限300/30s缓存/IGNORED_TREE_DIRS)、readFileContent(100KB上限/二进制检测/语言识别/realpath+isInside 逃逸护栏)；基准 REPO_ROOT。
- 标注 ssh/kanban 域为 v1.x 移除（不在 v1 范围，仅记录存在）。

## 前端依赖
`infra/dashboard/src/api/index.js` 中调用本域的函数及读取字段：
- `fetchHooks(local)`（api/index.js:290）→ `GET /api/hooks[?local=1]`；调用方 `HooksView.vue` 读 `status.hooks`、`status.thirdParty`（HooksView.vue:110-111）
- `scanHooks()`（api/index.js:294）→ `GET /api/hooks/scan`；读 `native` / `repos` 数组
- `getHookStatus(local)`（api/index.js:298）→ `GET /api/hooks/status[?local=1]`
- `installHook(hookId, local, dryRun)`（api/index.js:302）→ `POST /api/hooks/install` body `{ hookId, local, dryRun }`；读响应 `res.success`、`res.error`（HooksView.vue:125-128）
- `uninstallHook(hookId, local, dryRun)`（api/index.js:306）→ `POST /api/hooks/uninstall` body `{ hookId, local, dryRun }`；读响应 `res.success`、`res.error`（HooksView.vue:132-135）
- `validateHooks()`（api/index.js:310）→ `GET /api/hooks/validate`
- Hook 渲染（`HookItem.vue`）读字段：`hook.installed`、`hook.id`、`hook.description`、`hook.matcher`、`hook.event`、`hook.path`
- HooksView 分组（HooksView.vue:91/94/100）读 `hook.source`（`"hooks/"` / `"global"` / `repos/...`）；第三方项读 `hook.command || hook.id`（HooksView.vue:53）；安装/卸载取 `hook.id || hook.hook_id`（HooksView.vue:120）

## 源引用
- /Users/kex/Code/project_kex/agent-hub/infra/server/routes/hooks.js:1-78
- /Users/kex/Code/project_kex/agent-hub/infra/server/services/hook-manager.js:1-59
- /Users/kex/Code/project_kex/agent-hub/infra/hooks.py:27-101（常量/元数据解析）、105-145（scan_hooks）、150-262（install/uninstall）、267-375（status/第三方/绝对路径探测）、380-420（argparse）、423-589（CLI 主流程）
- /Users/kex/Code/project_kex/agent-hub/infra/dashboard/src/api/index.js:288-312
- /Users/kex/Code/project_kex/agent-hub/infra/dashboard/src/components/HooksView.vue:24-140
- /Users/kex/Code/project_kex/agent-hub/infra/dashboard/src/components/HookItem.vue:2-19
