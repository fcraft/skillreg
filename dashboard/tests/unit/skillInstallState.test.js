import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildTargetStatusItems,
  computeSkillSyncSummary,
  formatInstallError,
  mergeBridgeTargetStatus,
  parseSyncExecutionResult,
  resolveProjectInstallTargets,
} from '../../src/sources/skillInstallState.js'

test('parseSyncExecutionResult rejects explicit failures and zero-synced no-ops', () => {
  assert.deepEqual(
    parseSyncExecutionResult({ success: false, stderr: 'Permission denied' }, { skillName: 'demo' }),
    { ok: false, message: 'Permission denied' },
  )
  assert.deepEqual(
    parseSyncExecutionResult(
      { success: true, stdout: 'No skills to sync (no matching skills in workspace: demo)', syncedCount: 0 },
      { skillName: 'demo' },
    ),
    { ok: false, message: 'No skills to sync (no matching skills in workspace: demo)' },
  )
  assert.deepEqual(
    parseSyncExecutionResult(
      { success: true, stdout: 'Synced 1 skill(s) to /tmp/skills', syncedCount: 1 },
      { skillName: 'demo' },
    ),
    { ok: true, message: 'Synced 1 skill(s) to /tmp/skills' },
  )
})

test('formatInstallError turns structured backend codes and generic 500s into clear guidance', () => {
  assert.match(
    formatInstallError({ code: 'unsafe-path', message: 'Symlink skill directories are not supported: /a/b' }),
    /符号链接.*\/a\/b/,
  )
  assert.match(
    formatInstallError({ code: 'ambiguous-target', message: 'Target name is ambiguous; use its ID' }),
    /重复冲突/,
  )
  assert.match(
    formatInstallError({ code: 'permission-denied', message: 'EACCES /opt/skills' }),
    /写入权限.*EACCES/,
  )
  assert.match(
    formatInstallError({ code: 'target-busy', message: 'Another sync is writing this target' }),
    /正在执行其他同步任务/,
  )
  assert.match(
    formatInstallError({ message: 'Internal Server Error' }),
    /服务端内部错误/,
  )
})

test('resolveProjectInstallTargets expands discovered agent dirs and falls back to project roots', () => {
  const project = { targets: ['/work/app-a', '/work/app-b'] }
  const discovered = {
    '/work/app-a': {
      agent_dirs: [
        { agent: 'claude', path: '/work/app-a/.claude/skills' },
        { agent: 'codex', path: '/work/app-a/.codex/skills' },
      ],
    },
    '/work/app-b': { agent_dirs: [] },
  }
  const destinations = resolveProjectInstallTargets(project, discovered)
  assert.deepEqual(
    destinations.map(d => d.path),
    ['/work/app-a/.claude/skills', '/work/app-a/.codex/skills', '/work/app-b'],
  )
})

test('buildTargetStatusItems preserves unambiguous target identifiers even with duplicate names', () => {
  const targets = [
    { id: 'id-1', name: 'claude', label: 'claude', path: '/home/u/.claude/skills' },
    { id: 'id-2', name: 'claude', label: 'claude', path: '/home/u/proj/.claude/skills' },
  ]
  const projectTargets = [
    {
      name: '/work/app/.codex/skills',
      path: '/work/app/.codex/skills',
      _projectName: 'App',
      _projectId: 'p-1',
      _projectRoot: '/work/app',
      _agent: 'codex',
    },
  ]
  const statusMap = {
    '/home/u/.claude/skills': 'unchanged',
    '/home/u/proj/.claude/skills': 'missing',
    '/work/app/.codex/skills': 'changed',
  }
  const items = buildTargetStatusItems(targets, projectTargets, statusMap)
  assert.equal(items.length, 3)
  assert.notEqual(items[0].key, items[1].key)
  assert.equal(items[0].target, 'id-1')
  assert.equal(items[1].target, 'id-2')
  assert.equal(items[2].target, '/work/app/.codex/skills')
  assert.equal(items[2].label, 'app · codex')
  assert.equal(items[2].icon, 'codex')
  assert.equal(items[0].icon, 'claude')
  assert.equal(items[2].status, 'changed')
})

test('computeSkillSyncSummary matches named targets by path and excludes missing from installed', () => {
  const targets = [
    { id: 'id-1', name: 'my-claude', path: '/home/u/.claude/skills' },
    { id: 'id-2', name: 'my-codex', path: '/home/u/.codex/skills' },
  ]
  const projectTargets = [
    { name: '/work/app/.claude/skills', path: '/work/app/.claude/skills' },
  ]
  const statusMap = {
    demo: {
      '/home/u/.claude/skills': 'unchanged',
      '/home/u/.codex/skills': 'missing',
      '/work/app/.claude/skills': 'changed',
    },
  }
  const summary = computeSkillSyncSummary(targets, projectTargets, statusMap, 'demo')
  assert.equal(summary.installed, 2)
  assert.equal(summary.ok, 1)
  assert.equal(summary.changed, 1)
  assert.equal(summary.missing, 1)
  assert.equal(summary.namedInstalled, 1)
  assert.equal(summary.namedOk, 1)
  assert.equal(summary.projInstalled, 1)
  assert.equal(summary.total, 3)
})

test('mergeBridgeTargetStatus preserves statuses for unrelated targets', () => {
  const existing = {
    demo: {
      '/home/u/.claude/skills': 'unchanged',
      '/work/app/.codex/skills': 'changed',
    },
  }
  const merged = mergeBridgeTargetStatus(existing, '/home/u/.claude/skills', [
    { name: 'demo', target: '/home/u/.claude/skills', status: 'changed' },
  ])
  assert.equal(merged.demo['/home/u/.claude/skills'], 'changed')
  assert.equal(merged.demo['/work/app/.codex/skills'], 'changed')
})
