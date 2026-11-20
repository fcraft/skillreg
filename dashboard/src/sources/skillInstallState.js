/**
 * Pure state, target-resolution, and error-formatting helpers for Skill Detail
 * installation and sync status views.
 */

import { resolveProviderIconKey } from './providerIcons.js'

export function extractSyncErrorMessage(result, fallback = '安装失败') {
  if (!result || typeof result !== 'object') return fallback
  const raw =
    (typeof result.stderr === 'string' && result.stderr.trim())
    || (typeof result.error === 'string' && result.error.trim())
    || (typeof result.message === 'string' && result.message.trim())
    || (typeof result.stdout === 'string' && result.stdout.trim())
  return raw || fallback
}

export function parseSyncExecutionResult(result, { skillName = null, fallback = '安装失败' } = {}) {
  if (!result || typeof result !== 'object') {
    return { ok: false, message: fallback }
  }
  if (result.success === false) {
    return { ok: false, message: extractSyncErrorMessage(result, fallback) }
  }
  const stdout = typeof result.stdout === 'string' ? result.stdout.trim() : ''
  if (skillName && (result.syncedCount === 0 || stdout.startsWith('No skills to sync'))) {
    return {
      ok: false,
      message: stdout || `未在当前 workspace 中找到 ${skillName}，未执行安装`,
    }
  }
  return { ok: true, message: stdout }
}

export function formatInstallError(err, fallback = '安装失败') {
  const code = err?.code || err?.details?.code || null
  const rawMessage = typeof err?.message === 'string' ? err.message.trim() : ''
  const detail = rawMessage && rawMessage !== 'Internal Server Error' ? rawMessage : ''

  switch (code) {
    case 'ambiguous-target':
      return detail
        ? `同步目标名称存在重复冲突，请改用具体目录路径或目标 ID（${detail}）`
        : '同步目标名称存在重复冲突，请改用具体目录路径或目标 ID'
    case 'not-found':
      return detail ? `未找到目标目录或配置：${detail}` : '未找到对应的同步目标'
    case 'unsafe-path':
      return detail
        ? `路径受安全策略拦截（不支持符号链接或非法目录）：${detail}`
        : '路径受安全策略拦截（不支持符号链接或非法目录）'
    case 'permission-denied':
      return detail ? `没有目标目录写入权限：${detail}` : '没有目标目录写入权限'
    case 'target-busy':
      return '目标目录正在执行其他同步任务，请稍后重试'
    case 'target-changed':
      return '目标目录内容在同步期间发生变化，请重试'
    case 'resource-limit':
      return detail ? `Skill 文件数量或体积超出同步限制：${detail}` : 'Skill 文件数量或体积超出同步限制'
    case 'conflict':
      return detail ? `目标存在差异冲突：${detail}` : '目标存在差异冲突'
    case 'invalid':
      return detail ? `无效的目标参数：${detail}` : '无效的目标参数'
    default:
      if (rawMessage === 'Internal Server Error') {
        return `${fallback}（服务端内部错误，请检查目标目录权限与路径配置）`
      }
      return rawMessage || fallback
  }
}

export function resolveProjectInstallTargets(project, discoveredMap = {}) {
  const roots = project?.targets || []
  const seen = new Set()
  const resolved = []

  for (const rootPath of roots) {
    const discovered = discoveredMap?.[rootPath]?.agent_dirs
    if (Array.isArray(discovered) && discovered.length > 0) {
      for (const dir of discovered) {
        if (!dir?.path || seen.has(dir.path)) continue
        seen.add(dir.path)
        resolved.push({
          path: dir.path,
          label: dir.agent ? `${dir.agent} (${dir.path})` : dir.path,
          agent: dir.agent || null,
          icon: resolveProviderIconKey(dir),
          root: rootPath,
        })
      }
    } else if (rootPath && !seen.has(rootPath)) {
      seen.add(rootPath)
      resolved.push({
        path: rootPath,
        label: rootPath,
        agent: null,
        icon: resolveProviderIconKey(rootPath),
        root: rootPath,
      })
    }
  }

  return resolved
}

function projectTargetDisplayLabel(target) {
  if (target?.label) return target.label
  const path = target?.path || target?.name || ''
  if (target?._agent) {
    const rootName = (target._projectRoot || '').split('/').filter(Boolean).pop()
    return rootName ? `${rootName} · ${target._agent}` : target._agent
  }
  const segments = path.split('/').filter(Boolean)
  if (segments.length >= 2 && segments[segments.length - 1] === 'skills') {
    const parent = segments[segments.length - 2].replace(/^\./, '')
    const grand = segments.length >= 3 ? segments[segments.length - 3] : ''
    return grand ? `${grand} · ${parent}` : parent
  }
  return segments[segments.length - 1] || path
}

export function buildTargetStatusItems(targets = [], projectTargets = [], statusMap = {}) {
  const result = []

  for (const t of targets) {
    const targetIdentifier = t.id || t.path
    result.push({
      key: `target:${targetIdentifier}`,
      target: targetIdentifier,
      label: t.label || t.name || t.path,
      path: t.path,
      relPath: t.relPath || null,
      builtin: Boolean(t.builtin),
      shared: Boolean(t.shared),
      agentKind: t.agentKind || null,
      icon: resolveProviderIconKey(t),
      _project: false,
      status: statusMap[t.path] || 'not-installed',
    })
  }

  for (const t of projectTargets) {
    const targetPath = t.path || t.name
    result.push({
      key: `project:${t._projectId || t._projectName || ''}:${targetPath}`,
      target: targetPath,
      label: projectTargetDisplayLabel(t),
      path: targetPath,
      agentKind: t._agent || t.agentKind || null,
      icon: resolveProviderIconKey(t),
      _project: true,
      _projectName: t._projectName,
      status: statusMap[targetPath] || 'not-installed',
    })
  }

  return result
}

export function computeSkillSyncSummary(targets = [], projectTargets = [], statusMap = {}, skillName) {
  const namedPathSet = new Set(targets.map(t => t.path))
  const totalTargets = targets.length + projectTargets.length
  const targetsForSkill = statusMap?.[skillName]
  const summary = {
    installed: 0,
    changed: 0,
    missing: 0,
    ok: 0,
    total: totalTargets,
    namedOk: 0,
    namedInstalled: 0,
    projInstalled: 0,
  }
  if (!targetsForSkill) return summary

  for (const [targetPath, st] of Object.entries(targetsForSkill)) {
    const isInstalled = st === 'unchanged' || st === 'changed'
    if (st === 'unchanged') summary.ok++
    else if (st === 'changed') summary.changed++
    else if (st === 'missing') summary.missing++

    if (!isInstalled) continue

    summary.installed++
    if (namedPathSet.has(targetPath)) {
      summary.namedInstalled++
      if (st === 'unchanged') summary.namedOk++
    } else {
      summary.projInstalled++
    }
  }

  return summary
}

export function mergeBridgeTargetStatus(existingStatusMap = {}, targetKey, rows = []) {
  const next = {}
  for (const [skillName, targets] of Object.entries(existingStatusMap)) {
    const copy = { ...targets }
    if (targetKey && copy[targetKey] !== undefined) {
      delete copy[targetKey]
    }
    if (copy.custom !== undefined) {
      delete copy.custom
    }
    next[skillName] = copy
  }
  if (Array.isArray(rows)) {
    for (const row of rows) {
      if (!row?.name) continue
      const key = row.target === 'custom' ? targetKey : row.target
      if (!key) continue
      next[row.name] = next[row.name] || {}
      next[row.name][key] = row.status
    }
  }
  return next
}
