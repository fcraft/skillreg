import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  BUILTIN_PROVIDER_ICON_IDS,
  DEFAULT_PROVIDER_ICON,
  PROVIDER_ICON_ALIASES,
  PROVIDER_ICON_DEFS,
  getProviderIcon,
  hasProviderIcon,
  inferProviderIconFromPath,
  resolveProviderIconKey,
  scopeSvgIds,
} from '../../src/sources/providerIcons.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ICONS_DIR = path.resolve(__dirname, '../../src/assets/provider-icons')

const ALL_BUILTIN_AGENT_IDS = [
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
  // Legacy agents
  'tclaude',
  'tcodex',
  'agent',
]

function assertValidOfflineSvg(svg, label) {
  assert.equal(typeof svg, 'string', `${label}: svg must be a string`)
  assert.match(
    svg,
    /^<svg\s[^>]*xmlns="http:\/\/www\.w3\.org\/2000\/svg"[^>]*viewBox="[^"]+"[^>]*>[\s\S]+<\/svg>$/,
    `${label}: must be a complete SVG element with xmlns and viewBox`,
  )
  assert.match(svg, /<(path|rect|circle|polygon|polyline|line|ellipse)\b/, `${label}: must contain vector primitives`)
  assert.doesNotMatch(svg, /<script\b/i, `${label}: must not contain <script>`)
  assert.doesNotMatch(svg, /<filter\b/i, `${label}: must not rely on SVG <filter>`)
  assert.doesNotMatch(svg, /href="https?:/i, `${label}: must be 100% offline with no external URLs`)
  assert.doesNotMatch(svg, /url\(https?:/i, `${label}: must not reference remote URLs`)
}

test('all 31 built-in provider IDs (28 mainstream + 3 legacy) are 100% covered with valid offline SVG', () => {
  const catalog = fs.readFileSync(path.resolve(__dirname, '../../../src/skillreg/services/agent_catalog.py'), 'utf-8')
  const catalogIcons = [...catalog.matchAll(/\bicon="([^"]+)"/g)].map(match => match[1])
  assert.equal(catalogIcons.length, 31)
  for (const icon of catalogIcons) {
    assert.ok(PROVIDER_ICON_DEFS[icon], `Backend icon ${icon} must be registered`)
  }

  for (const agentId of ALL_BUILTIN_AGENT_IDS) {
    assert.equal(hasProviderIcon(agentId), true, `Expected built-in icon for ${agentId}`)
    const icon = getProviderIcon(agentId, { idPrefix: `t-${agentId}` })
    assert.notEqual(icon.key, DEFAULT_PROVIDER_ICON, `${agentId} must not fall back to custom`)
    assert.equal(icon.isFallback, false, `${agentId} should not be marked as fallback`)
    assertValidOfflineSvg(icon.svg, agentId)
  }

  for (const iconId of BUILTIN_PROVIDER_ICON_IDS) {
    assert.ok(PROVIDER_ICON_DEFS[iconId], `Missing PROVIDER_ICON_DEFS entry for ${iconId}`)
    assertValidOfflineSvg(PROVIDER_ICON_DEFS[iconId].svg, iconId)
  }
})

test('localized .svg asset files match iconData.js and ATTRIBUTION.md 1:1', () => {
  const attribution = fs.readFileSync(path.join(ICONS_DIR, 'ATTRIBUTION.md'), 'utf-8')
  const svgFilesOnDisk = fs
    .readdirSync(ICONS_DIR)
    .filter(file => file.endsWith('.svg'))
    .map(file => file.slice(0, -4))
    .sort()

  const registeredKeys = Object.keys(PROVIDER_ICON_DEFS).sort()
  assert.deepEqual(svgFilesOnDisk, registeredKeys)

  for (const key of registeredKeys) {
    const fileContent = fs.readFileSync(path.join(ICONS_DIR, `${key}.svg`), 'utf-8').trim()
    assert.equal(fileContent, PROVIDER_ICON_DEFS[key].svg, `${key}.svg must stay in sync with iconData.js`)
    assertValidOfflineSvg(fileContent, `${key}.svg`)
    assert.ok(
      attribution.includes(`\`${key}\``),
      `ATTRIBUTION.md must document license and source for \`${key}\``,
    )
  }
})

test('provider aliases and legacy identifiers resolve cleanly', () => {
  for (const [alias, expected] of Object.entries(PROVIDER_ICON_ALIASES)) {
    assert.equal(resolveProviderIconKey(alias), expected, `alias ${alias} -> ${expected}`)
    assert.equal(hasProviderIcon(alias), true, `alias ${alias} should count as built-in`)
  }
  assert.equal(resolveProviderIconKey('CLAUDE-CODE'), 'claude')
  assert.equal(resolveProviderIconKey('shared-agents'), 'agents')
  assert.equal(getProviderIcon('tclaude').isLegacy, true)
  assert.equal(getProviderIcon('tcodex').isLegacy, true)
  assert.equal(getProviderIcon('agent').isLegacy, true)
  assert.equal(getProviderIcon('agents').isShared, true)
})

test('path suffix inference distinguishes nested conventions and normalizes Windows separators', () => {
  assert.equal(inferProviderIconFromPath('~/.gemini/config/skills'), 'antigravity')
  assert.equal(inferProviderIconFromPath('/home/user/.gemini/skills'), 'gemini')
  assert.equal(inferProviderIconFromPath('~/.config/opencode/skills'), 'opencode')
  assert.equal(inferProviderIconFromPath('/work/app/.opencode/skills'), 'opencode')
  assert.equal(inferProviderIconFromPath('/home/u/.pi/agent/skills'), 'pi')
  assert.equal(inferProviderIconFromPath('/home/u/.omp/agent/skills'), 'omp')
  assert.equal(inferProviderIconFromPath('/home/u/.kimi/skills'), 'kimi')
  assert.equal(inferProviderIconFromPath('/home/u/.factory/skills'), 'droid')
  assert.equal(inferProviderIconFromPath('C:\\Users\\alice\\.cursor\\skills'), 'cursor')
  assert.equal(inferProviderIconFromPath('/srv/custom/skills'), null)
})

test('custom and unknown targets fall back to valid generic custom SVG', () => {
  const cases = [
    null,
    undefined,
    '',
    'unknown-provider-xyz',
    { id: '11111111-2222-3333-4444-555555555555', name: 'Custom Local', path: '/opt/my-skills' },
    { icon: 'custom', path: '/tmp/arbitrary' },
    { agentKind: 'nonexistent', path: '/tmp/arbitrary' },
  ]

  for (const input of cases) {
    const icon = getProviderIcon(input)
    assert.equal(icon.key, DEFAULT_PROVIDER_ICON)
    assert.equal(icon.isFallback, true)
    assertValidOfflineSvg(icon.svg, 'custom-fallback')
  }
})

test('multicolor provider icons scope gradient IDs per instance to avoid DOM collisions', () => {
  for (const key of ['codebuddy', 'workbuddy']) {
    const a = getProviderIcon(key, { idPrefix: 'instA' })
    const b = getProviderIcon(key, { idPrefix: 'instB' })
    assert.equal(a.multicolor, true)
    assert.equal(b.multicolor, true)
    assertValidOfflineSvg(a.svg, `${key}:A`)
    assertValidOfflineSvg(b.svg, `${key}:B`)
    assert.match(a.svg, /id="instA-/)
    assert.match(a.svg, /url\(#instA-/)
    assert.match(b.svg, /id="instB-/)
    assert.match(b.svg, /url\(#instB-/)
    assert.notEqual(a.svg, b.svg)
  }

  // codebuddy and workbuddy must produce visually distinct SVGs
  assert.notEqual(PROVIDER_ICON_DEFS.codebuddy.svg, PROVIDER_ICON_DEFS.workbuddy.svg)
  // scopeSvgIds is a safe no-op when no id exists
  assert.equal(scopeSvgIds(PROVIDER_ICON_DEFS.claude.svg, 'p1'), PROVIDER_ICON_DEFS.claude.svg)
})
