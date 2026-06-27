# import + git + submodules 域 API 契约

> 逆向自 agent-hub `infra/server/routes/import.js` + `infra/server/services/importer.js` + `infra/server/routes/git.js` + `infra/server/services/git-log.js` + `infra/server/routes/submodules.js` + `infra/server/services/submodule-manager.js` + `infra/dashboard/src/api/index.js`。
> 基准根目录：`REPO_ROOT`。

---

## import 域

### Endpoints

#### `POST /api/import/upload` — 上传并解压 zip
- 请求：`multipart/form-data`，字段 `file`
- 响应（200）：`{ success: true, data: { tempPath, extractedRoot } }`
  - `tempPath`：临时目录绝对路径（`<tmpdir>/agent-hub-import-<uuid>`）
  - `extractedRoot`：含 `SKILL.md` 的目录绝对路径（BFS 查找最浅层）
- 校验：文件前 2 字节必须为 `PK`（0x50 0x4b），否则 400
- 错误：400 `{ success: false, error: 'No file uploaded' | 'Invalid file...' | 'File is not a valid ZIP archive...' }`

#### `POST /api/import/validate` — 验证导入源
- 请求：body `{ sourceType: string, sourcePath: string }`
- 响应（200）：`{ success: true, data: ValidationResult }`
  - `ValidationResult`：
    ```typescript
    {
      valid: boolean,
      error?: string,          // valid=false 时
      skillName?: string,      // valid=true 时
      description?: string,
      fileCount?: number,
      conflict?: { exists: boolean, existingPath: string | null }
    }
    ```
- 校验链：路径存在 → 是目录 → 有 `SKILL.md` → frontmatter 有 `name` → `isValidSkillName(name)`

#### `POST /api/import/execute` — 执行 skill 导入
- 请求：body `{ sourceType, sourcePath, tempPath?, renameTo?, force? }`
- 响应（200）：`{ success: true, data: { name, skillPath, commit, filesCopied } }`
- 底层：`registerSkill({ sourcePath, force, renameTo, action: 'register' })`，完成后 `cleanupTemp(tempPath)`

#### `POST /api/import/preview-update` — 预览 skill 更新
- 请求：body `{ sourcePath: string, skillName: string }`
- 响应（200）：`{ success: true, data: { summary: { unchanged, added, modified, removed }, files: [{ path, status }] } }`
  - `files` 排序：modified → added → removed → unchanged，同 status 按 path 字母序
- 错误：400 `{ error: 'sourcePath and skillName are required' }`；404 `{ error: "skill 'X' does not exist..." }`

#### `POST /api/import/execute-update` — 执行 skill 更新
- 请求：body `{ sourcePath, skillName, tempPath? }`
- 响应（200）：`{ success: true, data: { name, skillPath, commit, filesCopied } }`
- 底层：`registerSkill({ sourcePath, force: true, renameTo: skillName, action: 'update' })`

#### `POST /api/import/git-clone` — 克隆 git 仓库并发现 skill
- 请求：body `{ url: string, branch?: string }`
- 响应（200）：`{ success: true, data: { tempPath, skills: [{ name, description, dirName, relPath }] } }`
- 底层：`git clone --depth 1 [--branch <branch>] <url> <tmpdir>/agent-hub-git-<uuid>`，然后 `discoverSkillsInDir`
- 错误：400 `{ error: 'url is required' | 'No SKILL.md found...' | 'Git clone failed...' }`

#### `POST /api/import/git-import` — 执行 git 导入（skill 或 submodule 模式）
- 请求：body `{ mode: 'skill' | 'submodule', ... }`
  - skill 模式：`{ mode: 'skill', tempPath, selectedSkills: string[], targetDir?: string }`
  - submodule 模式：`{ mode: 'submodule', url, branch?, targetPath }`
- 响应（200，skill 模式）：`{ success: true, data: { imported: [{ name, skillPath, filesCopied }], targetPath, commit } }`
- 响应（200，submodule 模式）：`{ success: true, data: { submodulePath, url, branch, commit } }`
- skill 模式底层：`gitImportSkills` → 复制到 `skills/<targetDir>/<name>/` → `git add -A && git commit`
- submodule 模式底层：`gitImportAsSubmodule` → `git submodule add [-b <branch>] <url> <targetPath>` → `git add && git commit`

#### `POST /api/import/cleanup` — 清理临时目录
- 请求：body `{ tempPath: string }`
- 响应（200）：`{ success: true, data: { cleaned: true } }`
- 安全：`tempPath` 必须在 `tmpdir()` 下，否则 400

### isValidSkillName

```javascript
/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(name)
```

### registerSkill 内部行为

1. 解析 `sourcePath`（`resolveHome`）
2. 验证：存在 → 是目录 → 有 `SKILL.md` → frontmatter 有 `name`
3. `name = renameTo || frontmatter.name`，校验 `isValidSkillName`
4. 检查 `skills/<name>/` 是否存在：存在且 `!force` → 409；`force` → 删除旧目录
5. `copySkillFiles(src, skills/<name>/)`（跳过隐藏文件除 `.gitignore`、跳过 `__pycache__`）
6. 更新 `sync-skills.json`（仅 sources 模式）
7. `git add skills/<name> [infra/sync-skills.json] [dashboard/data.json]`
8. `git commit -m "skillreg: register '<name>'"`（或 `update`）
9. 返回 `{ name, skillPath: 'skills/<name>', commit, filesCopied }`

### copySkillFiles 规则

- 跳过目录：`__pycache__` / 以 `.` 开头的目录
- 跳过文件：以 `.` 开头但非 `.gitignore` 的文件
- macOS 清理：跳过 `._*` 前缀文件

---

## git 域

### `GET /api/git/logs` — 获取 git 提交历史
- 请求：
  - query `scope?: 'all' | 'main' | 'submodule'`（默认 `'all'`）
  - query `path?: string`（scope=submodule 时指定 submodule 路径）
- 响应（200）：
  ```typescript
  {
    main: LogEntry[],              // 主仓日志（scope=all 或 main）
    submodules: { [path: string]: LogEntry[] }  // submodule 日志
  }
  ```
  - `LogEntry`：`{ hash, message, author, date }`
  - 主仓：`git log --format="%H<SEP>%s<SEP>%an<SEP>%aI" -n 15`
  - submodule：`git log --format=... -n 10`
- scope 行为：
  - `main`：只取主仓日志
  - `submodule`：只取指定 `path` 的 submodule 日志
  - `all`：主仓 + 所有 submodule 日志

---

## submodules 域

### `GET /api/submodules` — 列出所有 submodule 及状态
- 请求：无
- 响应（200）：`[{ path, branch, description, status: SubmoduleStatus }]`
  - `SubmoduleStatus` 结构见 registry 域契约（syncState 七态 + 指针字段）

### `POST /api/submodules/sync-preview` — 预览同步操作
- 请求：body `{ path: string }`
- 响应（200）：
  ```typescript
  {
    path: string,
    branch: string,
    ahead: number,
    behind: number,
    dirty: boolean,
    dirtyFiles: string[],
    detached: boolean,
    indexAhead: number,
    indexBehind: number,
    indexDirty: boolean,
    actions: string[],       // 人类可读的操作列表
    warnings: string[],      // 警告信息
    needsConfirmation: boolean  // 是否需要用户确认（如 diverged）
  }
  ```
- 底层：`fetch origin` → 检查 detached → 检查 dirty → 检查 ahead/behind → 检查指针偏移
- 错误：400 `{ error: 'Missing path' | 'Directory not found...' | 'Submodule not initialized...' }`

### `POST /api/submodules/diff` — 只读 diff（dirty tracked 文件）
- 请求：body `{ path: string }`
- 响应（200）：`{ path, branch, files: [{ path, status, diff }] }`
  - `status`：`'modified' | 'deleted' | 'added' | 'renamed'`
  - `diff`：unified diff 文本（`git diff HEAD -- <file>`）
- 只含 tracked dirty 文件，跳过 untracked（`??`）

### `POST /api/submodules/sync` — 同步单个 submodule
- 请求：body `{ path: string, commitMessage?: string }`
- 响应（200）：`{ success: true, actions: string[] }`
- 同步步骤：
  1. 修复 detached HEAD → `checkout <branch>`
  2. `fetch origin`
  3. dirty → `git add -u && git commit`
  4. behind > 0 → `git pull --rebase origin <branch>`（冲突自动 abort + rollback）
  5. ahead > 0 → `git push origin <branch>`（失败自动 rollback）
  6. 更新主仓库指针 → `git add <path> && git commit && git push`
- 错误：400 `{ error: 'Missing path' | ... }`；500 `{ error: 'Rebase 冲突...' | 'Push 失败...' }`

### `POST /api/submodules/refresh` — 只读远程检查
- 请求：body `{ path?: string }`（省略 path = 刷新所有）
- 响应（200，单个）：`{ path, status: SubmoduleStatus, error: string | null }`
- 响应（200，全部）：`{ results: [...], checkedAt: number }`
- 底层：`git fetch origin <branch>`（不碰 working tree），然后重算 status
- 并发：全部刷新时最多 6 个并发 fetch

### `POST /api/submodules/fix-detached` — 修复 detached HEAD
- 请求：body `{ path: string }`
- 响应（200）：`{ fixed: boolean, branch?, before?, after? }` 或 `{ fixed: false, message: 'HEAD is not detached' }`
- 底层：`git checkout <branch>`

## 前端依赖

`infra/dashboard/src/api/index.js` 中调用本域的函数：

### import 域
- `importUploadZip(file)` → `POST /api/import/upload`（FormData）；读取 `res.data.{ tempPath, extractedRoot }`
- `importValidate(body)` → `POST /api/import/validate`；读取 `res.data`（ValidationResult）
- `importExecute(body)` → `POST /api/import/execute`；读取 `res.data.{ name, skillPath, commit, filesCopied }`
- `importPreviewUpdate(body)` → `POST /api/import/preview-update`；读取 `res.data.{ summary, files }`
- `importExecuteUpdate(body)` → `POST /api/import/execute-update`
- `importCleanup(tempPath)` → `POST /api/import/cleanup`
- `importGitClone(url, branch)` → `POST /api/import/git-clone`；读取 `res.data.{ tempPath, skills }`
- `importGitExecute(body)` → `POST /api/import/git-import`；读取 `res.data`

### git 域
- `fetchGitLogs(scope, path)` → `GET /api/git/logs?scope=...&path=...`；读取 `{ main, submodules }`

### submodules 域
- `fetchSubmodules()` → `GET /api/submodules`；读取 `[{ path, branch, description, status }]`
- `syncSubmodule(path, commitMessage)` → `POST /api/submodules/sync`
- `previewSyncSubmodule(path)` → `POST /api/submodules/sync-preview`
- `fetchSubmoduleDiff(path)` → `POST /api/submodules/diff`
- `fixDetachedHead(path)` → `POST /api/submodules/fix-detached`
- `refreshSubmodule(path)` → `POST /api/submodules/refresh`（path 为空时刷新全部）

## 源引用

- `infra/server/routes/import.js:1-140` — 全部 import 路由
- `infra/server/services/importer.js:1-520` — validateImportSource / extractZip / executeImport / previewUpdate / executeUpdate / cleanupTemp / gitCloneToTemp / gitImportSkills / gitImportAsSubmodule / discoverSkillsInDir / findSkillMdDir / buildFileMap / hashFile
- `infra/server/routes/git.js:1-20` — git logs 路由
- `infra/server/services/git-log.js:1-70` — getLogs / parseLogs
- `infra/server/routes/submodules.js:1-90` — 全部 submodules 路由
- `infra/server/services/submodule-manager.js:1-320` — getSubmoduleDiff / previewSyncSubmodule / syncSubmodule / isSubmoduleInitialized / getSubmoduleConfig / parsePorcelain
- `infra/dashboard/src/api/index.js:180-340` — import/git/submodules 域前端函数
