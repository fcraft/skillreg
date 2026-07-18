import assert from 'node:assert/strict'
import test from 'node:test'

import { searchCommands } from '../../src/search/searchCommands.js'

function command(id, title, options = {}) {
  return {
    id,
    title,
    description: options.description || '',
    keywords: options.keywords || [],
    section: options.section || 'skill',
  }
}

test('keeps catalog order when the query is blank', () => {
  const commands = [command('b', 'Beta'), command('a', 'Alpha')]

  assert.deepEqual(searchCommands(commands, '  ').map(item => item.id), ['b', 'a'])
})

test('ranks exact title matches above prefixes and descriptions across sections', () => {
  const commands = [
    command('description', 'Workspace', { description: 'Open ntdev-build details', section: 'navigation' }),
    command('prefix', 'ntdev-build-page'),
    command('exact', 'ntdev-build'),
  ]

  assert.deepEqual(searchCommands(commands, 'ntdev-build').map(item => item.id), [
    'exact',
    'prefix',
    'description',
  ])
})

test('prefers title segment matches over keyword and description matches', () => {
  const commands = [
    command('description', 'Deploy helper', { description: 'Build and install an APK' }),
    command('keyword', 'NTDev tools', { keywords: ['build'] }),
    command('segment', 'ntdev-build'),
  ]

  assert.deepEqual(searchCommands(commands, 'build').map(item => item.id), [
    'segment',
    'keyword',
    'description',
  ])
})

test('requires every query token while allowing matches across searchable fields', () => {
  const commands = [
    command('page', 'ntcompose-build-page'),
    command('other', 'ntcompose-preview', { description: 'Build a preview bundle' }),
    command('missing', 'ntcompose-build'),
  ]

  assert.deepEqual(searchCommands(commands, 'build page').map(item => item.id), ['page'])
})

test('searches aliases, types, and repository paths through keywords', () => {
  const commands = [
    command('repo-skill', 'ask-matt', { keywords: ['Reference', 'repos/third/mattpocock-skills'] }),
    command('cli-skill', 'ntdev-build', { keywords: ['CLI', 'repos/k-cli/skill'] }),
  ]

  assert.deepEqual(searchCommands(commands, 'mattpocock').map(item => item.id), ['repo-skill'])
  assert.deepEqual(searchCommands(commands, 'CLI').map(item => item.id), ['cli-skill'])
})

test('normalizes full-width characters and separators', () => {
  const commands = [command('sync', 'Sync 工具')]

  assert.deepEqual(searchCommands(commands, 'ＳＹＮＣ').map(item => item.id), ['sync'])
  assert.deepEqual(searchCommands(commands, 'sync-工具').map(item => item.id), ['sync'])
})

test('uses a stable title order when match quality is equal', () => {
  const commands = [
    command('gamma', 'gamma-helper', { keywords: ['tool'] }),
    command('alpha', 'alpha-helper', { keywords: ['tool'] }),
  ]

  assert.deepEqual(searchCommands(commands, 'tool').map(item => item.id), ['alpha', 'gamma'])
})
