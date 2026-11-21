import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  buildPresetDraft,
  classifyTargets,
  detectedByLabel,
  formatAgentDisplayPath,
  normalizeTarget,
  partitionAgentCatalog,
  pickQuickPresets,
  resolveTargetExecuteKey,
  targetBadgeText,
} from '../../src/sources/agentTargets.js'

test('formatAgentDisplayPath prefers relPath and normalizes Unix/Windows home paths', () => {
  assert.equal(formatAgentDisplayPath('/home/alice/.claude/skills', '.claude/skills'), '~/.claude/skills')
  assert.equal(formatAgentDisplayPath('/Users/alice/.config/opencode/skills'), '~/.config/opencode/skills')
  assert.equal(formatAgentDisplayPath('/root/.codex/skills'), '~/.codex/skills')
  assert.equal(formatAgentDisplayPath('C:\\Users\\alice\\.cursor\\skills'), '~/.cursor/skills')
  assert.equal(formatAgentDisplayPath('/opt/custom/skills'), '/opt/custom/skills')
})

test('classifyTargets separates custom targets from auto-detected built-in targets', () => {
  const result = classifyTargets([
    { id: 'c1', name: 'my-dir', path: '/tmp/custom' },
    { id: 'b1', name: 'Claude Code', path: '/home/u/.claude/skills', builtin: true, agentKind: 'claude' },
    { id: 'b2', name: 'Shared Agents', path: '/home/u/.agents/skills', source: 'builtin', shared: true, agentKind: 'agents' },
  ])

  assert.equal(result.all.length, 3)
  assert.equal(result.custom.length, 1)
  assert.equal(result.builtin.length, 2)
  assert.equal(result.custom[0].icon, 'custom')
  assert.equal(result.builtin[0].icon, 'claude')
  assert.equal(result.builtin[1].icon, 'agents')
  assert.equal(targetBadgeText(result.custom[0]), '')
  assert.equal(targetBadgeText(result.builtin[0]), '自动识别')
  assert.equal(targetBadgeText(result.builtin[1]), '内置 · 共享')
})

test('detectedByLabel explains detection signal clearly', () => {
  assert.equal(detectedByLabel('directory'), '已检测到配置目录')
  assert.equal(detectedByLabel('skills'), '已检测到已有 Skills')
  assert.equal(detectedByLabel('binary', 'codex'), '已检测到 CLI (codex)')
  assert.equal(detectedByLabel(null), '未检测到')
})

test('partitionAgentCatalog splits detected and preset agents and filters by aliases or paths', () => {
  const catalog = [
    { id: 'claude', name: 'Claude Code', aliases: ['claude-code'], rel_path: '.claude/skills', path: '/home/u/.claude/skills', detected: true, active: true, configured: false },
    { id: 'opencode', name: 'OpenCode', aliases: ['oc'], rel_path: '.config/opencode/skills', path: '/home/u/.config/opencode/skills', detected: false, active: false, configured: false },
    { id: 'droid', name: 'Droid', aliases: ['factory'], rel_path: '.factory/skills', path: '/home/u/.factory/skills', detected: false, active: false, configured: false },
  ]

  const all = partitionAgentCatalog(catalog)
  assert.deepEqual(all.detected.map(a => a.id), ['claude'])
  assert.deepEqual(all.presets.map(a => a.id), ['opencode', 'droid'])

  const byAlias = partitionAgentCatalog(catalog, 'factory')
  assert.equal(byAlias.detected.length, 0)
  assert.deepEqual(byAlias.presets.map(a => a.id), ['droid'])

  const byPath = partitionAgentCatalog(catalog, '.config/opencode')
  assert.deepEqual(byPath.presets.map(a => a.id), ['opencode'])
})

test('buildPresetDraft and pickQuickPresets prepare preset inputs while skipping configured/legacy items', () => {
  const draft = buildPresetDraft({
    id: 'cursor',
    name: 'Cursor',
    path: '/home/u/.cursor/skills',
    rel_path: '.cursor/skills',
  })
  assert.deepEqual(draft, {
    name: 'Cursor',
    path: '/home/u/.cursor/skills',
    agentKind: 'cursor',
  })

  const quick = pickQuickPresets([
    { id: 'claude', name: 'Claude Code', detected: true, active: true, configured: true, legacy: false },
    { id: 'tclaude', name: 'tclaude', detected: false, active: false, configured: false, legacy: true },
    { id: 'codex', name: 'Codex', detected: true, active: true, configured: false, legacy: false },
    { id: 'cursor', name: 'Cursor', detected: true, active: false, configured: false, legacy: false },
    { id: 'opencode', name: 'OpenCode', detected: false, active: false, configured: false, legacy: false },
  ], 3)
  assert.deepEqual(quick.map(a => a.id), ['cursor', 'opencode', 'codex'])
})

test('resolveTargetExecuteKey uses canonical path instead of display label', () => {
  const normalized = normalizeTarget({
    id: 'uuid-1',
    name: 'Claude Code',
    path: '/home/u/.claude/skills',
    builtin: true,
  })
  assert.equal(resolveTargetExecuteKey(normalized), '/home/u/.claude/skills')
  assert.equal(resolveTargetExecuteKey('/custom/path'), '/custom/path')
})
