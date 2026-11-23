/**
 * Pure state helpers for built-in coding agent directories and sync targets.
 */

import { resolveProviderIconKey } from './providerIcons.js'

export function formatAgentDisplayPath(targetPath, relPath = null) {
  if (relPath && !String(relPath).startsWith('/') && !/^[A-Za-z]:[\\/]/.test(String(relPath))) {
    return `~/${String(relPath).replace(/^\/+/, '')}`
  }
  if (!targetPath) return ''
  const normalized = String(targetPath).replace(/\\/g, '/')

  const unixHomeMatch = normalized.match(/^\/Users\/[^/]+(?=\/|$)|^\/home\/[^/]+(?=\/|$)|^\/root(?=\/|$)/i)
  if (unixHomeMatch) {
    const suffix = normalized.slice(unixHomeMatch[0].length).replace(/^\/+/, '')
    return suffix ? `~/${suffix}` : '~'
  }

  const windowsHomeMatch = normalized.match(/^[A-Za-z]:\/Users\/[^/]+(?=\/|$)/i)
  if (windowsHomeMatch) {
    const suffix = normalized.slice(windowsHomeMatch[0].length).replace(/^\/+/, '')
    return suffix ? `~/${suffix}` : '~'
  }

  return targetPath
}

export function normalizeTarget(raw) {
  if (!raw || typeof raw !== 'object') return null
  const path = raw.path || ''
  const name = raw.name || raw.label || path
  const builtin = Boolean(raw.builtin || raw.source === 'builtin')
  return {
    ...raw,
    id: raw.id || null,
    name,
    label: raw.label || name,
    path,
    builtin,
    source: builtin ? 'builtin' : (raw.source || 'custom'),
    agentKind: raw.agentKind || null,
    icon: resolveProviderIconKey(raw),
    detectedBy: raw.detectedBy || null,
    exists: raw.exists ?? true,
    shared: Boolean(raw.shared),
    readsShared: Boolean(raw.readsShared),
    relPath: raw.relPath || null,
  }
}

export function classifyTargets(targets = []) {
  const all = (targets || []).map(normalizeTarget).filter(Boolean)
  const custom = all.filter(t => !t.builtin)
  const builtin = all.filter(t => t.builtin)
  return { all, custom, builtin }
}

export function targetBadgeText(target) {
  if (!target) return ''
  if (target.builtin) {
    return target.shared ? '内置 · 共享' : '内置'
  }
  return ''
}

export function detectedByLabel(detectedBy, detectedBinary = null) {
  if (detectedBy === 'directory') return '已检测到配置目录'
  if (detectedBy === 'skills') return '已检测到已有 Skills'
  if (detectedBy === 'binary') {
    return detectedBinary ? `已检测到 CLI (${detectedBinary})` : '已检测到 CLI 程序'
  }
  return '未检测到'
}

export function partitionAgentCatalog(agents = [], query = '') {
  const tokens = String(query || '')
    .trim()
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)

  const matches = (agent) => {
    if (!tokens.length) return true
    const haystack = [
      agent.id,
      agent.agent,
      agent.name,
      ...(agent.aliases || []),
      agent.rel_path,
      agent.path,
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
    return tokens.every(token => haystack.includes(token))
  }

  const filtered = (agents || []).filter(matches)
  return {
    detected: filtered.filter(agent => Boolean(agent.detected)),
    presets: filtered.filter(agent => !agent.detected),
  }
}

export function buildPresetDraft(agent) {
  if (!agent) return { name: '', path: '', agentKind: null }
  return {
    name: agent.name || agent.id || agent.agent || '',
    path: agent.path || (agent.rel_path ? `~/${agent.rel_path}` : ''),
    agentKind: agent.id || agent.agent || null,
  }
}

export function resolveTargetExecuteKey(target) {
  if (!target) return ''
  if (typeof target === 'string') return target
  return target.path || target.id || target.name || ''
}

export function pickQuickPresets(agents = [], limit = 8) {
  const available = agents.filter(agent => !agent.added && !agent.legacy)
  const { detected, presets } = partitionAgentCatalog(available)
  return [...detected, ...presets].slice(0, limit)
}

export function needsAgentOnboarding(catalog) {
  return catalog.onboarding === 'pending' && (
    !catalog.hasTargets || catalog.agents.some(agent => agent.detected && !agent.added)
  )
}
