import { test } from 'node:test'
import assert from 'node:assert/strict'
import { isActiveRun, statusLabel, observedSummary } from '../../src/sources/remoteSyncState.js'

test('remote observations keep installation state separate from run and connection state', () => {
  assert.equal(observedSummary(null), '尚未检查')
  assert.equal(observedSummary({ error: { message: 'offline' } }), '检查失败 · offline')
  assert.equal(observedSummary({ skills: [{ status: 'synced' }, { status: 'modified' }, { status: 'missing' }] }), '1 已同步 · 1 有差异 · 1 未安装')
  assert.equal(statusLabel('succeeded'), '已完成')
  assert.equal(statusLabel('online'), '连接正常')
  assert.ok(isActiveRun({ state: 'running' }))
  assert.ok(!isActiveRun({ state: 'failed' }))
})
