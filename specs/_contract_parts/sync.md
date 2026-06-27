# sync 域 API 契约

> 逆向自 agent-hub `infra/server/routes/sync.js` + `infra/server/services/sync-manager.js` + `infra/sync-skills.py` + `infra/dashboard/src/api/index.js`。
> 基准根目录：`REPO_ROOT`（= `infra/sync-skills.py` 的 `SCRIPT_DIR.parent`）；配置文件：`infra/sync-skills.json`；project 注册表：`~/.skillreg/projects.json`。

## 配置结构

### `infra/sync-skills.json`（sync-skills.py 权威配置）

```json
{
  "schema_version": 2,
  "targets": [
    { "name": "claude", "path": "~/.claude/skills", "skills": ["skill-a", "skill-b"] }
  ],
  "sources": [
    { "path": "skills/my-skill", "mode": "skill" },
    { "path": "repos/my-cli/skill", "mode": "scan" }
  ],
  "exclude_dirs": ["__pycache__", ".git", ".venv", "infra", "specs", "logs", "node_modules", "venv"],
  "exclude_files": ["*.pyc", ".DS_Store"],
  "manifest": {
    "enabled": true,
    "skip_unchanged": true,
    "file": ".sync-manifest.json"
  }
}
```

- `targets[].skills`：可选，指定该 target 只同步列出的 skill（省略 = 全量同步）。
- `sources`：可选白名单模式；省略时走全量扫描发现（`discover_skill_paths`）。
- `manifest.skip_unchanged`：基于 hash 跳过未变更文件。

### `~/.skillreg/projects.json`（project 注册表）

```json
{
  "projects": {
    "<uuid>": {
      "id": "<uuid>",
      "name": "my-project",
      "targets": ["/abs/path/to/.claude/skills", "/abs/path/to/.codex/skills"],
      "created_at": "2026-01-01T00:00:00.000Z"
    }
  }
}
```

- `targets` 存储的是 `resolveHome()` 后的绝对路径。

## Endpoints

### `GET /api/sync/config` — 获取完整 sync-skills.json
- 请求：无
- 响应（200）：完整 `infra/sync-skills.json` 对象
- 错误：500 `{ error: string }`

### `GET /api/sync/status` — 获取各 target 各 skill 的同步状态
- 请求：
  - query `target?: string`（指定单个 target）
  - query `include_projects?: 'true'`（附带 project 组内 target 的状态）
  - query `skill?: string`（按 skill 名过滤）
- 响应（200）：数组 `[{ target, name, status, _project?, _projectId? }]`
  - `target`：target 名或路径（`custom` 被 remap 为实际路径）
  - `name`：skill 名
  - `status`：sync 状态字符串（来自 `sync-skills.py --status` 的 TSV 输出第三列）
  - `_project` / `_projectId`：仅 `include_projects=true` 时附带
- 状态来源：`sync-skills.py --status --config <path> [--target <t>]` 的 stdout，按 `\t` 分三列解析

### `GET /api/sync/targets` — target 列表 + 状态概览
- 请求：无
- 响应（200）：`[{ name, path, status: { [skillName]: statusString } }]`

### `POST /api/sync/targets` — 添加 target
- 请求：body `{ name: string, path: string }`
- 响应（200）：`{ success: true, target: { name, path } }`
- 错误：400 `{ error: 'Missing name or path' }`；409 `{ error: 'Target "X" already exists' }`

### `DELETE /api/sync/targets/:name` — 删除 target
- 请求：path param `name`
- 响应（200）：`{ success: true, removed: string }`
- 错误：404 `{ error: 'Target "X" not found' }`

### `PUT /api/sync/targets/:name/skills` — 更新 target 的 skill 白名单
- 请求：body `{ skills: string[] }`
- 响应（200）：`{ success: true, target: string, skillCount: number }`
- 错误：400 `{ error: 'Missing skills array' | 'Unknown target: X' }`

### `PUT /api/sync/targets/:name/rename` — 重命名 target
- 请求：body `{ newName: string }`
- 响应（200）：`{ success: true, target: { name, path } }`
- 错误：400 `{ error: 'Missing newName' }`；404 `{ error: 'Target "X" not found' }`；409 `{ error: 'Target "Y" already exists' }`

### `POST /api/sync/execute` — 执行同步（支持 target 或 project）
- 请求：body `{ target?: string, project?: string, skills?: string[], dryRun?: boolean }`
- 响应（200，target 模式）：`{ success: boolean, stdout: string, stderr: string }`
- 响应（200，project 模式）：`{ project: string, results: [{ target, success, stdout, stderr }] }`
- 错误：400 `{ error: 'Missing target or project' }`
- 底层：`sync-skills.py --target <t> --config <path> [--dry-run] [skill1 skill2 ...]`，超时 60s

### `GET /api/sync/skill-presence?skill=...` — 某 skill 在各 target 的存在状态
- 请求：query `skill: string`
- 响应（200）：`{ skill: string, targets: { [targetName]: statusString } }`
- 错误：400 `{ error: 'Missing skill param' }`

### `GET /api/sync/target-skills?target=...` — 列出 target 中的 skill（managed/unmanaged）
- 请求：query `target: string`
- 响应（200）：JSON（来自 `sync-skills.py --list-target <t> --config <path>` 的 stdout）
- 错误：400 `{ error: 'Missing target param' }`

### `GET /api/sync/diff?skill=...&target=...` — 文件级 diff
- 请求：query `skill: string`, `target: string`
- 响应（200）：`[{ path, status: 'added'|'removed'|'modified'|'unchanged' }]`
- 底层：`sync-skills.py --diff <skill> --target <t> --config <path>`

### `POST /api/sync/remove-skill` — 从 target 移除 skill
- 请求：body `{ skill: string, target: string, force?: boolean }`
- 响应（200）：JSON（来自 `sync-skills.py --remove-from-target`）
- 错误：400 `{ error: 'Missing skill or target' }`

### `GET /api/sync/target-file?skill=...&target=...&path=...` — 读取 target 中的文件
- 请求：query `skill`, `target`, `path`
- 响应（200）：同 files 域 `readFileContent` 返回结构（`{ content, language, size }` 或 `{ binary, size }`）
- 错误：400 `{ error: 'Missing skill or target param' }`

### `GET /api/sync/discover-home` — 自动发现 ~/ 下的 agent 目录
- 请求：无
- 响应（200）：`{ agent_dirs: [{ agent, rel_path, path }] }`

### `GET /api/sync/discover?path=...` — 自动发现指定路径下的 agent 目录
- 请求：query `path: string`
- 响应（200）：`{ path: string, agent_dirs: [{ agent, path }] }`
- 错误：400 `{ error: 'Missing path param' }`

### `GET /api/sync/projects` — 列出所有 project
- 请求：无
- 响应（200）：`[project]`（project 结构见配置部分）

### `POST /api/sync/projects` — 创建 project
- 请求：body `{ name: string, targets: string[] }`
- 响应（200）：`{ success: true, project: project }`
- 错误：400 `{ error: 'Missing name or targets' }`

### `GET /api/sync/projects/:id` — 获取 project 详情
- 请求：path param `id`（UUID 或 name，大小写不敏感）
- 响应（200）：project 对象
- 错误：404 `{ error: 'Project not found' }`

### `POST /api/sync/projects/:id/targets` — 向 project 添加 target
- 请求：body `{ path: string }`
- 响应（200）：`{ success: true, project: project }`
- 错误：400 `{ error: 'Missing path' }`；404 `{ error: 'Project not found: X' }`

### `DELETE /api/sync/projects/:id/targets` — 从 project 移除 target
- 请求：body `{ path: string }`
- 响应（200）：`{ success: true, project: project }`
- 错误：400 `{ error: 'Missing path' }`；404

### `DELETE /api/sync/projects/:id` — 删除 project
- 请求：path param `id`
- 响应（200）：`{ success: true }`
- 错误：404 `{ error: 'Project not found: X' }`

## 高危契约：target 解析三套逻辑差异

### 1. `resolveTargetArg`（sync-manager.js:192）— named 否则 raw
```js
function resolveTargetArg(target) {
  const config = readConfig()
  const found = config.targets.find(t => t.name === target)
  return found ? found.name : target  // 不匹配则原样返回（当 raw path 用）
}
```
- 行为：先匹配 named target，不匹配则**原样返回**作为 raw path。
- 用于：`listTargetSkills`、`getSkillDiff`、`removeSkillFromTarget`。
- **无启发式**：任何字符串不匹配 named 就当 raw path。

### 2. `_resolve_target_by_name_or_path`（sync-skills.py:675）— "看起来像路径"启发式
```python
def _resolve_target_by_name_or_path(targets, value):
    expanded = Path(value).expanduser()
    for t in targets:
        if t.name.lower() == value.strip().lower():
            return t
        if Path(t.path).expanduser() == expanded:
            return t
    # Not a named target — treat as raw path if it looks like one
    if value and ('/' in value or '~' in value):
        return SyncTarget(name=value.strip(), path=str(expanded))
    return None
```
- 行为：先匹配 named（大小写不敏感）或 path 精确匹配；不匹配时，**仅当含 `/` 或 `~`** 才当 raw path，否则返回 `None`。
- **启发式**："看起来像路径"才当 raw path，否则不处理。
- 用于：sync-skills.py 内部的单 target 解析。

### 3. `resolve_targets_for_sync`（sync-skills.py:709）— 只 named + agent-dir 自动发现 + fallback
```python
def resolve_targets_for_sync(targets, value):
    # Only match NAMED targets — do NOT use _resolve_target_by_name_or_path
    expanded = Path(value).expanduser()
    for t in targets:
        if t.name.lower() == value.strip().lower():
            return [t]
        if Path(t.path).expanduser() == expanded:
            return [t]
    # Not a named target — try auto-discovery
    discovered = discover_agent_hub_dirs(expanded)
    if discovered:
        return [SyncTarget(name=str(dir_path), path=str(dir_path))
                for _agent, dir_path in discovered]
    # Fallback: single target (backward compat)
    return [SyncTarget(name="custom", path=str(expanded))]
```
- 行为：只匹配 named（大小写不敏感）或 path 精确匹配；不匹配时走 **agent-dir 自动发现**（`discover_agent_hub_dirs`）；发现不到才 fallback 为单个 `custom` target。
- **无启发式但有多 target**：一个路径可能发现多个 agent 目录，返回多个 target。
- 用于：`sync-skills.py` 主同步流程的 `--target` 解析。

### 统一目标：显式三态

| 三态 | 语义 | 判定方式 |
|---|---|---|
| `named target` | 配置中已命名的 target | 精确匹配 `targets[].name`（大小写不敏感） |
| `raw path` | 用户直接指定的路径 | 显式标记为 raw path（非启发式） |
| `agent-dir 自动发现` | 扫描路径下的 agent 目录 | `discover_agent_hub_dirs(path)` |

- 消除"看起来像路径"启发式（#2 的 `'/' in value or '~' in value`）。
- 消除 `custom` remap hack（sync-manager.js `_parseStatus` 中 `target === 'custom'` → 实际路径）。

## agent 目录发现

### `discoverAgentDirs(rootPath)`（sync-manager.js）
- 读取 `infra/agent-conventions.json` → `AGENT_HUB_CONVENTIONS` env → `DEFAULT_CONVENTIONS`。
- 检查 `rootPath` 下是否存在一级 agent 目录（如 `.claude/`），存在则返回 `[{ agent, path }]`。

### `discoverHomeAgentDirs()`（sync-manager.js）
- 同上，但 root 为 `~`，额外返回 `rel_path` 字段。

### `discover_agent_hub_dirs(root_path)`（sync-skills.py:688）
- Python 等价实现，使用 `AGENT_HUB_CONVENTIONS` 常量（7 个约定）。
- 返回 `[(agent_name, Path)]` 元组列表。

### AGENT_HUB_CONVENTIONS（7 个约定）
```python
AGENT_HUB_CONVENTIONS = [
    (".claude/skills", "claude"),
    (".tclaude/skills", "tclaude"),
    (".codebuddy/skills", "codebuddy"),
    (".codex/skills", "codex"),
    (".tcodex/skills", "tcodex"),
    (".agents/skills", "agents"),
    (".agent/skills", "agent"),
]
```

## 前端依赖

`infra/dashboard/src/api/index.js` 中调用本域的函数：

- `fetchSyncConfig()` → `GET /api/sync/config`
- `fetchSyncStatus(target, includeProjects, skill)` → `GET /api/sync/status?...`
- `fetchSyncTargets()` → `GET /api/sync/targets`；读取 `[{ name, path, status }]`
- `addSyncTarget(name, path)` → `POST /api/sync/targets`
- `removeSyncTarget(name)` → `DELETE /api/sync/targets/:name`
- `updateTargetSkills(target, skills)` → `PUT /api/sync/targets/:name/skills`
- `renameSyncTarget(oldName, newName)` → `PUT /api/sync/targets/:name/rename`
- `executeSync(target, options)` → `POST /api/sync/execute`；读取 `res.success`
- `executeProjectSync(project, options)` → `POST /api/sync/execute` body `{ project, ... }`
- `fetchSkillPresence(skill)` → `GET /api/sync/skill-presence?skill=...`；读取 `{ skill, targets }`
- `fetchTargetSkills(target)` → `GET /api/sync/target-skills?target=...`
- `fetchSkillDiff(skill, target)` → `GET /api/sync/diff?...`；读取 `[{ path, status }]`
- `removeSkillFromTarget(skill, target, force)` → `POST /api/sync/remove-skill`
- `fetchTargetFile(skill, target, path)` → `GET /api/sync/target-file?...`
- `fetchDiscover(targetPath)` → `GET /api/sync/discover?path=...`；读取 `{ path, agent_dirs }`
- `discoverHomeAgentDirs()` → `GET /api/sync/discover-home`；读取 `{ agent_dirs }`
- `fetchProjects()` → `GET /api/sync/projects`
- `fetchProject(id)` → `GET /api/sync/projects/:id`
- `createProject(name, targets)` → `POST /api/sync/projects`
- `addProjectTarget(id, path)` → `POST /api/sync/projects/:id/targets`
- `removeProjectTarget(id, path)` → `DELETE /api/sync/projects/:id/targets`（body `{ path }`）
- `deleteProject(id)` → `DELETE /api/sync/projects/:id`

## 源引用

- `infra/server/routes/sync.js:1-280` — 全部 sync 路由
- `infra/server/services/sync-manager.js:1-400` — getConfig/getStatus/getTargets/addTarget/removeTarget/renameTarget/updateTargetSkills/executeSync/executeProjectSync/listTargetSkills/getSkillDiff/removeSkillFromTarget/getSkillPresence/resolveTargetArg/discoverAgentDirs/discoverHomeAgentDirs/project CRUD
- `infra/sync-skills.py:675-770` — `_resolve_target_by_name_or_path` / `resolve_targets_for_sync` / `discover_agent_hub_dirs` / `compute_skill_diff`
- `infra/sync-skills.py:1-50` — `REPO_ROOT` / `AGENT_HUB_CONVENTIONS` / `EXCLUDED_DISCOVERY_DIR_NAMES`
- `infra/server/lib/agent-conventions.js:1-50` — `DEFAULT_CONVENTIONS` / `loadConventions`
- `infra/dashboard/src/api/index.js:100-180` — sync 域前端函数
