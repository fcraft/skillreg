/**
 * Unified API client for dashboard.
 * All requests go through /api/* which Vite proxies to the backend server.
 */

class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
    this.name = 'ApiError'
  }
}

async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({ error: res.statusText }))
    throw new ApiError(res.status, data.error || res.statusText)
  }
  return res.json()
}

function get(path) {
  return request(path)
}

function post(path, body) {
  return request(path, { method: 'POST', body: JSON.stringify(body) })
}

function put(path, body) {
  return request(path, { method: 'PUT', body: JSON.stringify(body) })
}

function del(path, body) {
  return request(path, {
    method: 'DELETE',
    ...(body ? { body: JSON.stringify(body) } : {}),
  })
}

// --- Workspace ---

export function fetchCurrentWorkspace() {
  return get('/api/workspace/current')
}

export function switchWorkspace(path) {
  return post('/api/workspace/switch', { path })
}

// --- Skills ---

export function fetchSkills() {
  return get('/api/skills')
}

export function fetchSkillsLite() {
  return get('/api/skills')
}

export function fetchSkillsFull() {
  return get('/api/skills?full=1')
}

export function fetchSkillRelationships(id) {
  return get(`/api/skills/${encodeURIComponent(id)}/relationships`)
}

export function fetchSkillStats(id) {
  return get(`/api/skills/${encodeURIComponent(id)}/stats`)
}

export function fetchSkillsRefresh() {
  return get('/api/skills/refresh')
}

export function fetchSkillDetail(id) {
  return get(`/api/skills/${encodeURIComponent(id)}`)
}

// Delete a standalone skill (skills/<name>). Repo-owned skills are rejected by
// the backend — remove the whole repo instead. Renaming skills is unsupported.
export function deleteSkill(id) {
  return del(`/api/skills/${encodeURIComponent(id)}`)
}

export function fetchSkillTree(id) {
  return get(`/api/skills/${encodeURIComponent(id)}/tree`)
}

export function fetchSkillFile(id, path) {
  return get(`/api/skills/${encodeURIComponent(id)}/file?path=${encodeURIComponent(path)}`)
}

export async function exportSkill(id) {
  const res = await fetch(`/api/skills/${encodeURIComponent(id)}/export`)
  if (!res.ok) {
    const data = await res.json().catch(() => ({ error: res.statusText }))
    throw new ApiError(res.status, data.error || res.statusText)
  }
  const blob = await res.blob()
  const disposition = res.headers.get('Content-Disposition') || ''
  const match = disposition.match(/filename="?([^"]+)"?/)
  const filename = match ? decodeURIComponent(match[1]) : `${id}.zip`
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// --- Sync ---

export function fetchSyncConfig() {
  return get('/api/sync/config')
}

export function fetchSyncStatus(target, includeProjects = false, skill = null) {
  const params = []
  if (target) params.push(`target=${encodeURIComponent(target)}`)
  if (includeProjects) params.push('include_projects=true')
  if (skill) params.push(`skill=${encodeURIComponent(skill)}`)
  const qs = params.length ? `?${params.join('&')}` : ''
  return get(`/api/sync/status${qs}`)
}

export function fetchSyncTargets() {
  return get('/api/sync/targets')
}

export function addSyncTarget(name, path) {
  return post('/api/sync/targets', { name, path })
}

export function removeSyncTarget(name) {
  return del(`/api/sync/targets/${encodeURIComponent(name)}`)
}

export function updateTargetSkills(target, skills) {
  return put(`/api/sync/targets/${encodeURIComponent(target)}/skills`, { skills })
}

export function executeSync(target, options = {}) {
  return post('/api/sync/execute', { target, ...options })
}

export function fetchSkillPresence(skill) {
  return get(`/api/sync/skill-presence?skill=${encodeURIComponent(skill)}`)
}

export function fetchTargetSkills(target) {
  return get(`/api/sync/target-skills?target=${encodeURIComponent(target)}`)
}

export function fetchSkillDiff(skill, target) {
  return get(`/api/sync/diff?skill=${encodeURIComponent(skill)}&target=${encodeURIComponent(target)}`)
}

export function removeSkillFromTarget(skill, target, force = false) {
  return post('/api/sync/remove-skill', { skill, target, force })
}

export function fetchDiscover(targetPath) {
  return get(`/api/sync/discover?path=${encodeURIComponent(targetPath)}`)
}

export function fetchTargetFile(skill, target, path) {
  return get(`/api/sync/target-file?skill=${encodeURIComponent(skill)}&target=${encodeURIComponent(target)}&path=${encodeURIComponent(path)}`)
}

// --- Submodules ---

export function fetchSubmodules() {
  return get('/api/submodules')
}

export function syncSubmodule(path, commitMessage) {
  return post('/api/submodules/sync', commitMessage ? { path, commitMessage } : { path })
}

export function previewSyncSubmodule(path) {
  return post('/api/submodules/sync-preview', { path })
}

// Read-only diff of dirty (tracked, uncommitted) files in a submodule.
export function fetchSubmoduleDiff(path) {
  return post('/api/submodules/diff', { path })
}

export function fixDetachedHead(path) {
  return post('/api/submodules/fix-detached', { path })
}

// Read-only remote check: fetch origin and recompute sync status without
// touching the working tree / committing / pushing. Omit `path` to refresh all.
export function refreshSubmodule(path) {
  return post('/api/submodules/refresh', path ? { path } : {})
}

// Remove a repo/submodule from the workspace.
export function removeSubmodule(path) {
  return post('/api/submodules/remove', { path })
}

// Rename a repo/submodule directory (leaf name only; prefix preserved).
export function renameSubmodule(path, newName) {
  return post('/api/submodules/rename', { path, newName })
}

// --- Files ---

export function fetchFileTree(root) {
  const qs = root ? `?root=${encodeURIComponent(root)}` : ''
  return get(`/api/files/tree${qs}`)
}

export function fetchFileContent(root, path) {
  return get(`/api/files/content?root=${encodeURIComponent(root)}&path=${encodeURIComponent(path)}`)
}

// --- Git ---

export function fetchGitLogs(scope = 'all', path) {
  let qs = `?scope=${scope}`
  if (path) qs += `&path=${encodeURIComponent(path)}`
  return get(`/api/git/logs${qs}`)
}

// --- Projects ---

export function fetchProjects() {
  return get('/api/sync/projects')
}

export function fetchProject(id) {
  return get(`/api/sync/projects/${encodeURIComponent(id)}`)
}

export function createProject(name, targets) {
  return post('/api/sync/projects', { name, targets })
}

export function addProjectTarget(id, path) {
  return post(`/api/sync/projects/${encodeURIComponent(id)}/targets`, { path })
}

export function removeProjectTarget(id, path) {
  return del(`/api/sync/projects/${encodeURIComponent(id)}/targets`, { path })
}

export function deleteProject(id) {
  return del(`/api/sync/projects/${encodeURIComponent(id)}`)
}

export function executeProjectSync(project, options = {}) {
  return post('/api/sync/execute', { project, ...options })
}

// --- Sync - Target rename ---

export function renameSyncTarget(oldName, newName) {
  return put(`/api/sync/targets/${encodeURIComponent(oldName)}/rename`, { newName })
}

export function discoverHomeAgentDirs() {
  return get('/api/sync/discover-home')
}

// --- Import ---

export function importUploadZip(file) {
  const formData = new FormData()
  formData.append('file', file)
  return fetch('/api/import/upload', { method: 'POST', body: formData })
    .then(res => {
      if (!res.ok) return res.json().then(data => { throw new ApiError(res.status, data.error) })
      return res.json()
    })
    .then(res => res.data)
}

export function importValidate(body) {
  return post('/api/import/validate', body).then(res => res.data)
}

export function importExecute(body) {
  return post('/api/import/execute', body).then(res => res.data)
}

export function importPreviewUpdate(body) {
  return post('/api/import/preview-update', body).then(res => res.data)
}

export function importExecuteUpdate(body) {
  return post('/api/import/execute-update', body).then(res => res.data)
}

export function importCleanup(tempPath) {
  return post('/api/import/cleanup', { tempPath }).then(res => res.data)
}

export function importGitClone(url, branch) {
  return post('/api/import/git-clone', { url, branch }).then(res => res.data)
}

export function importGitExecute(body) {
  return post('/api/import/git-import', body).then(res => res.data)
}

// --- Hooks ---

export function fetchHooks(local = false) {
  return get(`/api/hooks${local ? '?local=1' : ''}`)
}

export function scanHooks() {
  return get('/api/hooks/scan')
}

export function getHookStatus(local = false) {
  return get(`/api/hooks/status${local ? '?local=1' : ''}`)
}

export function installHook(hookId, local = false, dryRun = false) {
  return post('/api/hooks/install', { hookId, local, dryRun })
}

export function uninstallHook(hookId, local = false, dryRun = false) {
  return post('/api/hooks/uninstall', { hookId, local, dryRun })
}

export function validateHooks() {
  return get('/api/hooks/validate')
}
