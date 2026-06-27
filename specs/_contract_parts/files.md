# files 域 API 契约

> 逆向自 agent-hub `infra/server/routes/files.js` + `infra/server/services/file-browser.js` + `infra/server/lib/paths.js`。仅记录现状契约，不含产品决策。
> 基准根目录：`REPO_ROOT`（= 环境变量 `AGENT_HUB_ROOT`，否则 `import.meta.url` 上溯 4 级）；`REPO_ROOT_REAL = realpathSync(REPO_ROOT)`。

## Endpoints

### `GET /api/files/tree` — 返回某目录的文件树（缓存 30s，深度≤4，节点≤300）

- 请求：
  - query `root?: string`（可选，默认 `'.'`；相对 `REPO_ROOT` 解析）
- 响应（200，直接返回树根节点对象，非包一层）：
  - `name: string` — 节点名；根节点恒为 `'.'`，其余为 `path.basename`
  - `path: string` — 相对 root 的 slash 路径（`toSlashPath`，根节点为 `''`）
  - `type: 'dir' | 'file'` — 节点类型
  - `children?: Array<node>` — 仅 `dir` 有；深度达 4 或节点数达 300 时不再展开（无 `children` 键）
- 遍历规则（源码 verbatim）：
  - `IGNORED_TREE_DIRS = { '.git', 'node_modules', '.venv', 'venv', '__pycache__', 'dist', 'build', 'coverage' }` 全部跳过
  - 任何以 `.` 开头的目录名也跳过（`entry.name.startsWith('.')`）—— 注意：以 `.` 开头的**文件**不在 tree 路径过滤内，但目录过滤会连带
  - 排序：目录优先于文件，同类型按 `localeCompare` 升序
  - 缓存：`treeCache = new Cache(30_000)`（30s TTL，键为 realpath 后的 root）；`clearCache()` 可清空
- 错误：
  - `403 { error: string }` — root 解析后 `!isInside(REPO_ROOT_REAL, root)`（越界），或 realpath/解析抛错（`err.message`）

### `GET /api/files/content` — 读取文件内容（≤100KB，含二进制检测/语言识别/逃逸护栏）

- 请求：
  - query `root?: string`（可选，默认 `'.'`；相对 `REPO_ROOT` 解析）
  - query `path: string`（必填，相对 root 的路径）
- 响应（200，文本文件）：
  - `content: string` — UTF-8 文件内容
  - `language: string` — 由扩展名映射（见下）；未知为 `'text'`
  - `size: number` — 文件字节数（`stat.size`）
- 响应（200，二进制文件）：
  - `binary: true`
  - `size: number`
- 安全护栏（源码 verbatim 顺序）：
  1. `!relativePath || relativePath.startsWith('/') || relativePath.split(/[\\/]/).includes('..')` → 400 `'Invalid file path'`
  2. `realpathSync(root)` + `realpathSync(resolve(root, relativePath))`，`!isInside(root, filePath)` → 403 `'File is outside base directory'`
  3. `!stat.isFile()` → 400 `'Path is not a file'`
  4. `stat.size > 100 * 1024` → 413 `'File is too large to preview'`（body 额外带 `size: stat.size`）
- 语言映射（`languageForPath`，扩展名小写）：
  - `.md→markdown` `.json→json` `.js/.mjs→javascript` `.ts→typescript` `.vue→vue` `.py→python` `.sh→shell` `.yml/.yaml→yaml` `.toml→toml` `.css→css` `.html→html`，其余 →`text`
- 二进制检测（`isBinaryBuffer`）：
  - 含 NUL 字节(0) → 二进制
  - 否则取前 512 字节样本，控制字符（`<7` 或 `>14 && <32`）占比 > 0.3 → 二进制
- 错误：
  - `400 { error: 'Invalid file path' }` / `{ error: 'Path is not a file' }`
  - `403 { error: 'File is outside base directory' }`
  - `413 { error: 'File is too large to preview', size: number }`
  - `500 { error: string }` — 其余未带 `err.status` 的异常（`err.status || 500`）

## 高危契约（按域适用）

- registry/skills 域必填：getAll() 返回 `{skills, repoNodes, submodules, relationships, generatedAt}`；skill 对象字段(id/name/description/type/graphType/parentNode/path/skillFilePath/fileCount/remoteUrl/parentSkill/isSubmodule/submodulePath)；repoNodes 字段(含 isSubmoduleRoot/branch)；graphType 四态(isolated-skill/cli-skill/repo-skill/repo-cli)及 skill/ 子路径判定；syncState 七态(synced/ahead/behind/diverged/dirty/missing/unknown)；submodule 指针 indexRef/indexAhead/indexBehind/indexDirty(indexDirty 不得砍)；ntdev DEBUG 残留位置(skill-registry.js:508-510 须清除)；classifySkillType(CLI vs Reference，向上找 pyproject.toml/src/*.py)。
- sync 域必填：三套 target 解析逻辑差异——resolveTargetArg(sync-manager.js:192，named 否则 raw)、_resolve_target_by_name_or_path(sync-skills.py:675，"看起来像路径"启发式)、resolve_targets_for_sync(sync-skills.py:709，只 named+agent-dir 自动发现+fallback)；统一目标显式三态 named/raw-path/agent-dir。config CRUD(getConfig/addTarget/removeTarget/renameTarget/updateTargetSkills)、project 注册表(~/.skillreg/projects.json)、discoverAgentDirs/discoverHomeAgentDirs。
- hooks 域：hook-manager.js 是 subprocess 壳(转发 hooks.py)，scan/status/install/uninstall/validate；hooks.py 用 @hook-* 注解发现，写 ~/.claude/settings.json(--local 写项目级)。
- import 域：三来源(zip upload/git-clone --depth 1/本地目录)×两模式(skill 复制到 skills/<name>/、submodule add 到 repos/)+update(preview/execute)；registerSkill 内部 git add/commit；isValidSkillName 正则 `[A-Za-z0-9][A-Za-z0-9_-]*`。
- files 域（本域）：buildTree(深度4/节点上限300/30s缓存/IGNORED_TREE_DIRS)；readFileContent(100KB上限/二进制检测/语言识别/realpath+isInside 逃逸护栏)；基准 REPO_ROOT。
- 标注 ssh/kanban 域为 v1.x 移除（不在 v1 范围，仅记录存在）。

## 前端依赖

`infra/dashboard/src/api/index.js` 中调用本域的函数：

- `fetchFileTree(root)` → `GET /api/files/tree?root=<root>`（root 为空时不带 query）
  - 读取字段：树节点 `{name, path, type, children}`（递归）
- `fetchFileContent(root, path)` → `GET /api/files/content?root=<root>&path=<path>`
  - 读取字段：文本态 `{content, language, size}`；二进制态 `{binary, size}`

## 源引用

- `infra/server/routes/files.js:10-22` — GET /tree 路由与越界 403
- `infra/server/routes/files.js:25-38` — GET /content 路由与 err.status||500
- `infra/server/services/file-browser.js:6-8` — MAX_TREE_DEPTH=4 / MAX_TREE_NODES=300 / MAX_PREVIEW_BYTES=100*1024
- `infra/server/services/file-browser.js:10-13` — IGNORED_TREE_DIRS
- `infra/server/services/file-browser.js:15` — treeCache = new Cache(30_000)
- `infra/server/services/file-browser.js:20-71` — buildTree（节点 shape、'.' 目录过滤、排序、深度/节点上限）
- `infra/server/services/file-browser.js:76-105` — readFileContent（四道护栏 + 二进制/文本分支）
- `infra/server/services/file-browser.js:110-112` — clearCache
- `infra/server/lib/paths.js:6-9` — REPO_ROOT / REPO_ROOT_REAL / CONFIG_PATH
- `infra/server/lib/paths.js:12-15` — isInside
- `infra/server/lib/paths.js:26-44` — languageForPath 扩展名映射
- `infra/server/lib/paths.js:46-54` — isBinaryBuffer
- `infra/dashboard/src/api/index.js:190-197` — fetchFileTree / fetchFileContent
