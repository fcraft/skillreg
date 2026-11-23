import { expect, it } from 'vitest'
import { needsAgentOnboarding } from '../../src/sources/agentTargets.js'

it.each([
  ['pending', false, [], true],
  ['pending', true, [{ detected: true, added: false }], true],
  ['pending', true, [{ detected: true, added: true }, { detected: false, added: false }], false],
  ['skipped', false, [], false],
  ['completed', true, [{ detected: true, added: false }], false],
])('checks first visit with %s and hasTargets=%s', (onboarding, hasTargets, agents, expected) => {
  expect(needsAgentOnboarding({ onboarding, hasTargets, agents })).toBe(expected)
})
