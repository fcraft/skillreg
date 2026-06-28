# files + git + submodules + hooks 域迁 Python

## What to build

把 agent-hub 的 files / git / submodules / hooks 四个域从 Node 迁到 Python，补齐 dashboard 的浏览与历史能力。

**files 域**（迁 `infra/server/services/file-browser.js` ~150 行）：
- `buildTree`（文件树，深度 4、节点上限 300、30s 缓存）+ `readFileContent`（100KB 上限、二进制检测、语言识别）迁 Python（`pathlib` + `os.walk`）。
- 基准从 `REPO_ROOT` 切到 workspace 路径。
- 保留路径逃逸护栏（`isInside` / realpath 检查）。

**git 域**（迁 `infra/server/services/git-log.js` ~70 行）：
- 主仓 + submodule 日志（`git log` 调用）。
- 基准切到 workspace，submodule 列表从 **workspace 的 `.gitmodules`** 读取（复用 #3 registry 已建的 submodule 配置读取）。

**submodules 域**（迁 `infra/server/services/submodule-manager.js` ~310 行 + skill-registry.js 的 submodule 状态部分）：
- submodule 状态 / sync / `fixDetachedHead` / `refreshSubmoduleRemoteStatus`（并发 fetch）。
- 基准切到 workspace。

**hooks 域**（迁 `infra/hooks.py` + 删 `hook-manager.js` 壳）：
- `hook-manager.js` 是 subprocess 转发壳（转发 `infra/hooks.py`），**删除壳**，后端直接 import `hooks.py`（从 agent-hub 迁入并参数化 `REPO_ROOT` → workspace）。
- scan / status / install / uninstall / validate 五个操作。

**前端适配**：复制 `FileTree` / `FilePreview` / `GitLog` / `SubmoduleStatus` / `SubmoduleBadge` / `HooksView` / `HookItem`，改 `api/index.js` 适配。

来源代码：`infra/server/services/file-browser.js`、`infra/server/routes/files.js`、`infra/server/services/git-log.js`、`infra/server/routes/git.js`、`infra/server/services/submodule-manager.js`、`infra/server/routes/submodules.js`、`infra/hooks.py`、`infra/server/services/hook-manager.js`、`infra/server/routes/hooks.js`。

## Acceptance criteria

- [ ] dashboard 浏览 workspace 文件树（深度/节点上限行为与原一致）
- [ ] dashboard 预览文件内容（大小上限、二进制检测、语言识别）
- [ ] 路径逃逸护栏在 Python 版保留（不能访问 workspace 外文件）
- [ ] dashboard 显示主仓 + submodule 的 git 提交历史
- [ ] dashboard 显示 submodule 状态（syncState 七态、indexDirty 等，与 #3 契约一致）
- [ ] submodule sync / fixDetachedHead / 远程状态刷新可用
- [ ] hooks scan / status / install / uninstall / validate 可用，hooks.py 参数化为 workspace 基准
- [ ] hook-manager.js 转发壳已删除，后端直接 import hooks.py
- [ ] 所有基准从 REPO_ROOT 切到 workspace 路径

## Blocked by

- #1（API 契约）
- #3（registry 已建 submodule 配置读取，files/git/submodules 复用）
