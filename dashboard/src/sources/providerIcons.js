/**
 * Pure provider icon resolution and localized offline SVG lookup.
 *
 * All SVG markup is bundled locally under dashboard/src/assets/provider-icons/
 * (MIT / ISC open-source icons; see ATTRIBUTION.md). No external CDN is used.
 */

import { PROVIDER_ICON_DEFS } from '../assets/provider-icons/iconData.js'

export const DEFAULT_PROVIDER_ICON = 'custom'

export const BUILTIN_PROVIDER_ICON_IDS = Object.freeze([
  'agents',
  'claude',
  'codex',
  'cursor',
  'gemini',
  'antigravity',
  'copilot',
  'opencode',
  'codebuddy',
  'workbuddy',
  'pi',
  'cline',
  'droid',
  'kimi',
  'qwen',
  'qoder',
  'kiro',
  'crush',
  'vibe',
  'hermes',
  'dsh',
  'commandcode',
  'devin',
  'grok',
  'zcode',
  'alma',
  'omp',
  'minimax-code',
  'agent',
])

export const PROVIDER_ICON_ALIASES = Object.freeze({
  'shared': 'agents',
  'shared-agents': 'agents',
  'claude-code': 'claude',
  'tclaude': 'claude',
  'codex-cli': 'codex',
  'tcodex': 'codex',
  'cursor-cli': 'cursor',
  'cursor-agent': 'cursor',
  'gemini-cli': 'gemini',
  'agy': 'antigravity',
  'gh-copilot': 'copilot',
  'copilot-cli': 'copilot',
  'github-copilot': 'copilot',
  'oc': 'opencode',
  'codebuddy-code': 'codebuddy',
  'cbc': 'codebuddy',
  'workbuddy-ai': 'workbuddy',
  'pi-coding-agent': 'pi',
  'cline-cli': 'cline',
  'factory': 'droid',
  'factory-droid': 'droid',
  'kimi-code': 'kimi',
  'kimi-cli': 'kimi',
  'qwen-code': 'qwen',
  'qwen-cli': 'qwen',
  'qoder-cli': 'qoder',
  'qoder-cn': 'qoder',
  'kiro-cli': 'kiro',
  'mistral-vibe': 'vibe',
  'hermes-agent': 'hermes',
  'deepseek-harness': 'dsh',
  'command-code': 'commandcode',
  'devin-cli': 'devin',
  'grok-build': 'grok',
  'oh-my-pi': 'omp',
  'minimax': 'minimax-code',
})

// Ordered longest-suffix-first so nested conventions (e.g. .gemini/config/skills)
// match before shorter parents (.gemini/skills).
const PATH_SUFFIX_RULES = Object.freeze([
  [['.gemini', 'config', 'skills'], 'antigravity'],
  [['.config', 'opencode', 'skills'], 'opencode'],
  [['.config', 'crush', 'skills'], 'crush'],
  [['.config', 'devin', 'skills'], 'devin'],
  [['.config', 'alma', 'skills'], 'alma'],
  [['.pi', 'agent', 'skills'], 'pi'],
  [['.omp', 'agent', 'skills'], 'omp'],
  [['.agents', 'skills'], 'agents'],
  [['.claude', 'skills'], 'claude'],
  [['.codex', 'skills'], 'codex'],
  [['.cursor', 'skills'], 'cursor'],
  [['.gemini', 'skills'], 'gemini'],
  [['.copilot', 'skills'], 'copilot'],
  [['.opencode', 'skills'], 'opencode'],
  [['.codebuddy', 'skills'], 'codebuddy'],
  [['.workbuddy', 'skills'], 'workbuddy'],
  [['.pi', 'skills'], 'pi'],
  [['.cline', 'skills'], 'cline'],
  [['.factory', 'skills'], 'droid'],
  [['.kimi-code', 'skills'], 'kimi'],
  [['.kimi', 'skills'], 'kimi'],
  [['.qwen', 'skills'], 'qwen'],
  [['.qoder', 'skills'], 'qoder'],
  [['.kiro', 'skills'], 'kiro'],
  [['.vibe', 'skills'], 'vibe'],
  [['.hermes', 'skills'], 'hermes'],
  [['.dsh', 'skills'], 'dsh'],
  [['.commandcode', 'skills'], 'commandcode'],
  [['.grok', 'skills'], 'grok'],
  [['.zcode', 'skills'], 'zcode'],
  [['.minimax', 'skills'], 'minimax-code'],
  [['.tclaude', 'skills'], 'claude'],
  [['.tcodex', 'skills'], 'codex'],
  [['.agent', 'skills'], 'agent'],
])

const LEGACY_KEYS = new Set(['tclaude', 'tcodex', 'agent'])

export function normalizeIconIdentifier(value) {
  if (typeof value !== 'string') return ''
  return value.trim().toLowerCase()
}

export function lookupProviderIconKey(identifier) {
  const key = normalizeIconIdentifier(identifier)
  if (!key) return null
  if (Object.prototype.hasOwnProperty.call(PROVIDER_ICON_DEFS, key)) {
    return key
  }
  const aliased = PROVIDER_ICON_ALIASES[key]
  if (aliased && Object.prototype.hasOwnProperty.call(PROVIDER_ICON_DEFS, aliased)) {
    return aliased
  }
  return null
}

export function hasProviderIcon(identifier) {
  const resolved = lookupProviderIconKey(identifier)
  return Boolean(resolved && resolved !== DEFAULT_PROVIDER_ICON)
}

export function inferProviderIconFromPath(targetPath) {
  if (typeof targetPath !== 'string' || !targetPath.trim()) return null
  const parts = targetPath
    .replace(/\\/g, '/')
    .split('/')
    .map(segment => segment.trim().toLowerCase())
    .filter(segment => segment && segment !== '~' && segment !== '.')

  if (!parts.length) return null

  for (const [suffix, iconKey] of PATH_SUFFIX_RULES) {
    if (parts.length < suffix.length) continue
    let matched = true
    for (let i = 0; i < suffix.length; i += 1) {
      if (parts[parts.length - suffix.length + i] !== suffix[i]) {
        matched = false
        break
      }
    }
    if (matched) return iconKey
  }
  return null
}

export function resolveProviderIconKey(input) {
  if (!input) return DEFAULT_PROVIDER_ICON

  if (typeof input === 'string') {
    const direct = lookupProviderIconKey(input)
    if (direct) return direct
    return inferProviderIconFromPath(input) || DEFAULT_PROVIDER_ICON
  }

  if (typeof input === 'object') {
    // 1. Prefer explicit built-in icon / agent identifiers.
    const explicitCandidates = [
      input.icon,
      input._icon,
      input.agentKind,
      input.agent,
      input._agent,
    ]
    for (const candidate of explicitCandidates) {
      const resolved = lookupProviderIconKey(candidate)
      if (resolved && resolved !== DEFAULT_PROVIDER_ICON) {
        return resolved
      }
    }

    // 2. Check catalog item `id` only when it matches a built-in provider key/alias
    //    (configured targets use UUIDs for `id`, which will cleanly skip).
    const idResolved = lookupProviderIconKey(input.id)
    if (idResolved && idResolved !== DEFAULT_PROVIDER_ICON) {
      return idResolved
    }

    // 3. Infer from relPath / path suffixes for legacy or custom-named built-in paths.
    const pathCandidates = [input.relPath, input.rel_path, input.path]
    for (const candidate of pathCandidates) {
      const inferred = inferProviderIconFromPath(candidate)
      if (inferred) return inferred
    }
  }

  return DEFAULT_PROVIDER_ICON
}

export function scopeSvgIds(svg, idPrefix) {
  if (!svg || !idPrefix) return svg
  const safePrefix = String(idPrefix).replace(/[^a-zA-Z0-9_-]/g, '')
  if (!safePrefix) return svg

  const ids = new Set()
  svg.replace(/\bid="([^"]+)"/g, (_, id) => {
    ids.add(id)
    return _
  })
  if (!ids.size) return svg

  let scoped = svg
  for (const id of ids) {
    const nextId = `${safePrefix}-${id}`
    scoped = scoped
      .replaceAll(`id="${id}"`, `id="${nextId}"`)
      .replaceAll(`url(#${id})`, `url(#${nextId})`)
      .replaceAll(`href="#${id}"`, `href="#${nextId}"`)
  }
  return scoped
}

export function getProviderIcon(input, { idPrefix = '' } = {}) {
  const key = resolveProviderIconKey(input)
  const def = PROVIDER_ICON_DEFS[key] || PROVIDER_ICON_DEFS[DEFAULT_PROVIDER_ICON]
  const rawAgent = typeof input === 'object' && input
    ? normalizeIconIdentifier(input.agentKind || input.agent || input._agent || input.id || '')
    : normalizeIconIdentifier(typeof input === 'string' ? input : '')

  const isFallback = key === DEFAULT_PROVIDER_ICON
  const isShared = key === 'agents' || Boolean(typeof input === 'object' && input?.shared)
  const isLegacy = Boolean(
    (typeof input === 'object' && input?.legacy) || LEGACY_KEYS.has(rawAgent),
  )

  return {
    key,
    viewBox: def.viewBox,
    multicolor: Boolean(def.multicolor),
    isFallback,
    isShared,
    isLegacy,
    svg: idPrefix ? scopeSvgIds(def.svg, idPrefix) : def.svg,
  }
}

export { PROVIDER_ICON_DEFS }
