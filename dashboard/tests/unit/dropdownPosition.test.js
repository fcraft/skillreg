import assert from 'node:assert/strict'
import test from 'node:test'

import { positionDropdown } from '../../src/overlays/dropdownPosition.js'

const viewport = {
  viewportWidth: 1024,
  viewportHeight: 768,
  menuWidth: 168,
  menuHeight: 112,
}

test('aligns the dropdown with the trigger right edge', () => {
  assert.deepEqual(
    positionDropdown({ left: 900, right: 924, top: 100, bottom: 124 }, viewport),
    { left: 756, top: 128 },
  )
})

test('keeps the dropdown inside the viewport edges', () => {
  assert.deepEqual(
    positionDropdown({ left: 4, right: 28, top: 100, bottom: 124 }, viewport),
    { left: 8, top: 128 },
  )
})

test('opens above the trigger when there is not enough room below', () => {
  assert.deepEqual(
    positionDropdown({ left: 900, right: 924, top: 720, bottom: 744 }, viewport),
    { left: 756, top: 604 },
  )
})
