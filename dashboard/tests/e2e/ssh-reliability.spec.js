import { expect, test } from '@playwright/test'

const connection = { id: 'reliable-dev', name: '开发机', host: 'dev1', status: 'online' }
const target = { id: 'reliable-target', name: 'Codex', path: '/demo/.codex/skills', transport: 'ssh', connectionId: connection.id }
const plan = { id: 'reliable-preview', workspace: '/workspace', requiresOverwrite: false, targets: [{ target, skills: [{ name: 'demo-skill', status: 'missing', files: [] }] }] }

async function setup(page) {
  await page.route('**/api/connections', route => route.fulfill({ json: [connection] }))
  await page.route('**/api/targets', route => route.fulfill({ json: [target] }))
  await page.route('**/api/sync/observations', route => route.fulfill({ json: [] }))
  await page.route('**/api/sync/runs', route => route.fulfill({ json: [] }))
}

test('configuration failure is not an empty workspace and can be retried', async ({ page }) => {
  await setup(page)
  let failed = true
  await page.route('**/api/connections', route => failed
    ? route.fulfill({ status: 503, json: { detail: { message: '配置读取失败' } } })
    : route.fulfill({ json: [connection] }))
  await page.goto('/ssh')
  await expect(page.getByRole('alert')).toContainText('配置读取失败')
  await expect(page.getByRole('heading', { name: '连接你的开发机' })).toHaveCount(0)
  failed = false
  await page.getByRole('button', { name: '重新加载' }).click()
  await expect(page.locator('.ssh-directory')).toHaveCount(1)
  await expect(page.getByRole('alert')).toHaveCount(0)
})

test('changing selection invalidates an in-flight preview even when reselected', async ({ page }) => {
  await setup(page)
  let release, requests = 0
  const pending = new Promise(resolve => { release = resolve })
  await page.route('**/api/sync/preview', async route => {
    requests++
    await pending
    await route.fulfill({ json: plan })
  })
  await page.goto('/ssh')
  await page.getByRole('button', { name: 'Codex', exact: true }).click()
  await page.getByRole('button', { name: '从 workspace 安装', exact: true }).click()
  await page.getByLabel('搜索 Skill', { exact: true }).fill('demo-skill')
  await page.locator('.ssh-skill-list .q-checkbox').filter({ hasText: /^demo-skill[^-]/ }).click()
  const selection = page.locator('.ssh-skill-list .q-checkbox').filter({ hasText: /^demo-skill[^-]/ })
  await page.getByRole('button', { name: '检查状态并预览' }).click()
  await expect.poll(() => requests).toBe(1)
  await selection.click()
  await selection.click()
  const response = page.waitForResponse('**/api/sync/preview')
  release()
  await response
  await expect(page.getByRole('button', { name: '检查状态并预览' })).toBeEnabled()
  await expect(page.getByRole('dialog', { name: '确认同步内容' })).toHaveCount(0)
  await page.getByRole('button', { name: '检查状态并预览' }).click()
  await expect(page.getByRole('dialog', { name: '确认同步内容' })).toBeVisible()
})

test('run polling recovers without retaining a stale network error', async ({ page }) => {
  await setup(page)
  const run = { id: 'reliable-run', state: 'running', createdAt: '2026-09-08T00:00:00Z', workspace: '/workspace', progress: { completed: 0, total: 1 }, results: [{ target, state: 'running', skills: [] }] }
  let recovered = false
  await page.route('**/api/sync/runs', route => route.fulfill({ json: [run] }))
  await page.route('**/api/sync/runs/reliable-run', route => recovered
    ? route.fulfill({ json: { ...run, state: 'succeeded', progress: { completed: 1, total: 1 } } })
    : route.fulfill({ status: 503, json: { detail: { message: '进度连接中断' } } }))
  await page.goto('/ssh')
  await page.getByRole('button', { name: /执行记录/ }).click()
  await page.locator('.ssh-history-row').click()
  const dialog = page.getByRole('dialog', { name: '同步执行记录' })
  await expect(dialog.getByRole('alert')).toContainText('进度连接中断')
  recovered = true
  await expect(dialog).toContainText('1 / 1 项')
  await expect(dialog.getByRole('alert')).toHaveCount(0)
})
