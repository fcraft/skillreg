import assert from 'node:assert/strict'
import test from 'node:test'

import {
  gitIdentityRequestFromError,
  validateGitIdentity,
} from '../../src/sources/gitIdentity.js'

test('git identity error opens a request for the affected repository', () => {
  assert.deepEqual(
    gitIdentityRequestFromError({
      code: 'git_identity_required',
      details: { repository: 'repos/qqgen-ui-skills' },
    }),
    { repository: 'repos/qqgen-ui-skills' },
  )
  assert.equal(gitIdentityRequestFromError({ code: 'other_error' }), null)
})

test('git identity form requires a name and email', () => {
  assert.equal(validateGitIdentity('', 'user@example.com'), '请输入 Git 用户名')
  assert.equal(validateGitIdentity('Workspace User', 'invalid'), '请输入有效的 Git 邮箱')
  assert.equal(validateGitIdentity('Workspace User', 'user@example.com'), '')
})
