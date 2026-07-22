import test from 'node:test'
import assert from 'node:assert/strict'

import { canApplyUpdate, destructiveCount, requiresForce, sourceStatusLabel } from '../../src/sources/sourceState.js'

test('keeps source update states separate from target sync states', () => {
  assert.equal(sourceStatusLabel('up-to-date'), '已是最新')
  assert.equal(sourceStatusLabel('update-available'), '有可用更新')
  assert.equal(sourceStatusLabel('synced'), '尚未检查')
})

test('requires explicit force for local changes and blocks dirty repos', () => {
  const local = { token: 'preview', localModified: true, repoDirty: false, summary: { deleted: 2 } }
  assert.equal(requiresForce(local), true)
  assert.equal(destructiveCount(local), 2)
  assert.equal(canApplyUpdate(local), false)
  assert.equal(canApplyUpdate(local, true), true)
  assert.equal(canApplyUpdate({ ...local, repoDirty: true }, true), false)
})
