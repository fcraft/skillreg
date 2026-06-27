# registry + skills 域 API 契约

> 逆向自 agent-hub `infra/server/routes/registry.js` + `infra/server/routes/skills.js` + `infra/server/services/skill-registry.js` + `infra/server/services/registry.js` + `infra/dashboard/src/api/index.js`。
> 基准根目录：`REPO_ROOT`（= `paths.js` 的 `REPO_ROOT`，环境变量 `AGENT_HUB_ROOT` 或 `import.meta.url` 上溯 4 级）。

## Endpoints — skills 域

### `GET /api/skills` — skill 列表（轻量 / 完整）
- 请求：
  - query `full?: '1'`（完整模式，附带 repoNodes/submodules/relationships/gitLogs）
- 响应（200，轻量）：`{ skills: skill[], generatedAt: string }`
- 响应（200，完整）：`{ skills, repoNodes, submodules, relationships, generatedAt, gitLogs }`
  - `gitLogs` 来自 `getLogs('all')`（见 git 域契约）
- 底层：`getAll()` 返回 `{ skills, repoNodes, submodules, relationships, generatedAt }`，轻量模式只取 `skills` + `generatedAt`

### `GET /api/skills/refresh` — 强制刷新
- 请求：无
- 响应（200）：`{ skills, repoNodes, submodules, relationships, generatedAt, gitLogs }`
- 底层：`cache.clear()` 后重新 `getAll()` + `getLogs('all')`

### `GET /api/skills/:id` — 单个 skill 详情
- 请求：path param `id`（skill name）
- 响应（200）：skill 对象（见下）
- 错误：404 `{ error: 'Unknown skill' }`

### `GET /api/skills/:id/relationships` — 某 skill 的关系
- 请求：path param `id`
- 响应（200）：`{ skill: string, relationships: relationship[] }`
  - 过滤条件：`r.from === skillId || r.to === skillId || r.from === skill.name || r.to === skill.name`
- 错误：404 `{ error: 'Unknown skill' }`

### `GET /api/skills/:id/stats` — 某 skill 的统计
- 请求：path param `id`
- 响应（200）：`{ name, fileCount, type, path }`
- 错误：404 `{ error: 'Unknown skill' }`

### `GET /api/skills/:id/tree` — skill 文件树
- 请求：path param `id`
- 响应（200）：文件树根节点（同 files 域 `buildTree` 返回结构）
- 错误：403 `{ error: 'Skill path is outside repository' }`；404 `{ error: 'Unknown skill' }`

### `GET /api/skills/:id/file?path=...` — skill 文件内容
- 请求：path param `id`，query `path: string`
- 响应（200）：同 files 域 `readFileContent` 返回结构
- 错误：403 / 404 / 413（同 files 域）

### `GET /api/skills/:id/export` — 导出 skill 为 zip
- 请求：path param `id`
- 响应（200）：`application/zip` 二进制流，`Content-Disposition: attachment; filename="<name>.zip"`
- 排除：`.DS_Store` / `Thumbs.db` / `._*` / `.icloud*` / `__MACOSX` / `.git`
- 错误：403 `{ error: 'Skill path is outside repository' }`；404 `{ error: 'Unknown skill' }`

## Endpoints — registry 域

### `POST /api/registry/register` — 注册外部 skill
- 请求：body `{ sourcePath: string, force?: boolean }`
- 响应（200）：`{ success: true, data: { name, skillPath, commit, filesCopied } }`
- 错误：`{ success: false, error: string }`（400/404/409）

### `POST /api/registry/convert` — 将文件 skill 转为 CLI repo
- 请求：body `{ name: string }`
- 响应（200）：`{ success: true, data: { name, repoPath, skillPath } }`
- 错误：`{ success: false, error: string }`（400/404/409）

### `GET /api/registry/list` — 列出所有已注册 skill
- 请求：无
- 响应（200）：`{ success: true, data: { skills: [...] } }`

## 核心数据结构

### `getAll()` 返回结构（**原样冻结，最高危契约**）

```typescript
{
  skills: Skill[],           // 所有扫描到的 skill
  repoNodes: RepoNode[],     // 合成的 submodule 根节点
  submodules: Submodule[],   // submodule 配置 + 状态
  relationships: Relationship[],  // 依赖关系
  generatedAt: string        // ISO 时间戳
}
```

### Skill 对象字段

```typescript
{
  id: string,              // = parsed.name（SKILL.md frontmatter name）
  name: string,            // 同 id
  description: string | null,  // SKILL.md frontmatter description
  type: 'CLI' | 'Reference',   // classifySkillType 结果
  graphType: 'isolated-skill' | 'cli-skill' | 'repo-cli' | 'repo-skill',
  parentNode: string | null,   // 所属 submodule path，无则 null
  path: string,                // skill 目录的 repo 相对路径（slash）
  skillFilePath: string,       // SKILL.md 的 repo 相对路径（slash）
  fileCount: number,           // countSkillFiles 结果（上限 200 文件 / 6 层深度）
  remoteUrl: string | null,    // git remote URL（sshToHttps 规范化后）
  parentSkill: null,           // 恒为 null（预留字段）
  isSubmodule: boolean,        // 是否在 submodule 内
  submodulePath: string | null // 所属 submodule path，无则 null
}
```

### RepoNode 对象字段（合成的 submodule 根节点）

```typescript
{
  id: string,                  // = sub.path
  name: string,                // sub.path.replace('repos/', '')
  description: string,         // submodule 描述
  type: 'repo-cli' | 'repo-skill',  // classifySkillType(sub.path) 结果
  graphType: 'repo-cli' | 'repo-skill',  // 同 type
  parentNode: null,            // 恒为 null
  path: string,                // submodule path
  skillFilePath: null,         // 恒为 null
  fileCount: 0,                // 恒为 0
  remoteUrl: string | null,    // submodule remote URL
  parentSkill: null,           // 恒为 null
  isSubmodule: true,           // 恒为 true
  submodulePath: string,       // = sub.path
  isSubmoduleRoot: true,       // 恒为 true（区分于普通 skill）
  branch: string               // submodule 分支
}
```

### Submodule 对象字段

```typescript
{
  path: string,
  branch: string,
  description: string,
  remoteUrl: string | null,
  status: SubmoduleStatus      // 见下
}
```

### SubmoduleStatus 对象字段（**syncState 七态 + 指针字段**）

```typescript
{
  commit: string | null,       // submodule HEAD short SHA
  ahead: number,               // 领先 origin/<branch> 的提交数
  behind: number,              // 落后 origin/<branch> 的提交数
  dirty: boolean,              // working tree 是否有变更
  syncState: 'synced' | 'ahead' | 'behind' | 'diverged' | 'dirty' | 'missing' | 'unknown',
  isDetached: boolean,         // HEAD 是否 detached
  indexRef: string | null,     // 主仓库 git index 中记录的 submodule commit SHA
  indexAhead: number,          // 主仓库指针领先 submodule HEAD 的提交数
  indexBehind: number,         // 主仓库指针落后 submodule HEAD 的提交数
  indexDirty: boolean,         // 主仓库有未提交的 submodule 指针变更（**不得砍掉**）
  checkedAt: number | null     // 上次 fetch 时间戳（ms），无则 null
}
```

### syncState 七态判定逻辑

```
1. 目录不存在 → 'missing'
2. rev-list HEAD...origin/<branch> 失败 → 'unknown'
3. ahead > 0 && behind > 0 → 'diverged'
4. ahead > 0 → 'ahead'
5. behind > 0 → 'behind'
6. dirty (porcelain 非空) && 当前为 'synced' → 'dirty'
7. 否则 → 'synced'
```

### Relationship 对象

```typescript
{ from: string, to: string, type: 'contains' | 'depends-on' }
```
- `contains`：submodule 包含 skill（`from` = submodule path, `to` = skill name）
- `depends-on`：硬编码已知依赖（`KNOWN_DEPENDENCIES`）

## graphType 四态判定逻辑

```
1. 无 parentSubmodule → 'isolated-skill'
2. 有 parentSubmodule 且 skillDir 相对路径以 'skill/' 开头 → 'cli-skill'
3. 有 parentSubmodule 且 type === 'CLI' → 'repo-cli'
4. 有 parentSubmodule 且 type === 'Reference' → 'repo-skill'
```

- **`skill/` 子路径约定**：判定 `cli-skill` 靠 skill 目录是否在 submodule 的 `skill/` 子路径下（`relativePath.startsWith('skill/')`）。这是隐式契约，前端依赖画树。

## classifySkillType 逻辑

```javascript
function classifySkillType(dirPath) {
  // 从 dirPath 向上逐级查找
  for (let i = parts.length; i >= 1; i--) {
    const candidate = parts.slice(0, i).join('/')
    // 找到 pyproject.toml → 'CLI'
    if (existsSync(resolve(fullDir, 'pyproject.toml'))) return 'CLI'
    // 找到 src/ 目录且内有 *.py → 'CLI'
    if (existsSync(srcDir) && hasPyFiles(srcDir)) return 'CLI'
  }
  return 'Reference'
}
```

## URL 规范化

### `sshToHttps`（skill-registry.js:26）

```javascript
function sshToHttps(sshUrl) {
  if (!sshUrl) return null
  const match = sshUrl.match(/git@([^:]+):(.+?)(?:\.git)?$/)
  if (match) return `https://${match[1]}/${match[2]}`
  if (sshUrl.startsWith('http')) return sshUrl.replace(/\.git$/, '')
  return null
}
```

- 输入：`git@github.com:fcraft/skillreg.git` → 输出：`https://github.com/fcraft/skillreg`
- 输入：`https://github.com/fcraft/skillreg.git` → 输出：`https://github.com/fcraft/skillreg`
- 输入：`null` / 非 ssh 非 http → `null`

### `resolveRepoUrl`（remote-syncer.js:187）— 另一份独立实现

> **注意**：这是 sync 域 remote-syncer.js 中的另一份 URL 规范化实现，与 `sshToHttps` 逻辑相似但独立存在。v1 需收成单一 `server/lib/url.py`。

## ntdev DEBUG 残留（**必须清除**）

`skill-registry.js:508-510`（在 `getAll()` 的 repoNodes 合成循环内）：

```javascript
if (sub.path.includes('ntdev')) {
  console.error(`DEBUG: ${sub.path} isCliRepo=${isCliRepo} graphType=${graphType}`)
}
```

- 这段 DEBUG 代码会在每次 `getAll()` 调用时对路径含 `ntdev` 的 submodule 输出 stderr。
- 迁移时**必须清除**，不得保留。

## 扫描逻辑

### `discoverSkillPaths(dir = REPO_ROOT)`

- 递归扫描目录，找所有 `SKILL.md` 文件。
- `IGNORED_SCAN_DIRS`：`.git` / `.idea` / `.codebuddy` / `node_modules` / `dashboard` / `.venv` / `venv` / `__pycache__` / `dist` / `coverage`
- 以 `.` 开头的目录名也跳过。
- 返回 repo 相对路径列表（slash），按名称排序。

### `readSubmoduleConfigs()`

1. 读取 `.gitmodules`（`git config -f .gitmodules --list`），解析 `submodule.<name>.path/branch/url`。
2. 自动扫描已初始化的 submodule（目录下 `.git` 是 file 而非 directory → gitlink）。
3. 合并：`.gitmodules` 元数据优先，无则用 `getSubmoduleBranch(path)` 和 `deriveSubmoduleDescription(path)`。
4. 返回 `[{ path, branch, description }]`。

### 缓存

- `getAll()` 结果缓存 30s（`Cache(30_000)`）。
- `refresh()` 清空缓存。
- `refreshAllSubmodulesRemoteStatus()` 完成后清空缓存。

## 前端依赖

`infra/dashboard/src/api/index.js` 中调用本域的函数：

- `fetchSkills()` / `fetchSkillsLite()` → `GET /api/skills`；读取 `{ skills, generatedAt }`
- `fetchSkillsFull()` → `GET /api/skills?full=1`；读取 `{ skills, repoNodes, submodules, relationships, generatedAt, gitLogs }`
- `fetchSkillsRefresh()` → `GET /api/skills/refresh`
- `fetchSkillDetail(id)` → `GET /api/skills/:id`；读取 skill 对象全部字段
- `fetchSkillRelationships(id)` → `GET /api/skills/:id/relationships`
- `fetchSkillStats(id)` → `GET /api/skills/:id/stats`
- `fetchSkillTree(id)` → `GET /api/skills/:id/tree`
- `fetchSkillFile(id, path)` → `GET /api/skills/:id/file?path=...`
- `exportSkill(id)` → `GET /api/skills/:id/export`（下载 zip）

## 源引用

- `infra/server/routes/skills.js:1-200` — 全部 skills 路由
- `infra/server/routes/registry.js:1-40` — 全部 registry 路由
- `infra/server/services/skill-registry.js:1-100` — `sshToHttps` / `getRemoteUrl` / `discoverSkillPaths` / `parseSkillFile` / `classifySkillType`
- `infra/server/services/skill-registry.js:100-250` — `countSkillFiles` / `readSubmoduleConfigs` / `getSubmoduleBranch` / `deriveSubmoduleDescription`
- `infra/server/services/skill-registry.js:250-400` — `getSubmoduleStatus` / `getSubmoduleIndexStatus` / `isHeadDetached` / `getSubmoduleIndexRef` / `fixDetachedHead` / `refreshSubmoduleRemoteStatus` / `refreshAllSubmodulesRemoteStatus`
- `infra/server/services/skill-registry.js:400-550` — `getAll()` / `getSkill()` / `refresh()`
- `infra/server/services/registry.js:1-250` — `registerSkill` / `convertSkill` / `listRegisteredSkills` / `copySkillFiles` / `readSkillFrontmatter` / `isValidSkillName`
- `infra/dashboard/src/api/index.js:40-100` — skills 域前端函数
