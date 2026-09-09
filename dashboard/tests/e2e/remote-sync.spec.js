import { expect, test } from '@playwright/test'

test('SSH setup, discovery, overwrite confirmation and run polling', async ({ page }, testInfo) => {
  const connection = { id: 'ssh-ui-test', name: '测试开发机', host: 'dev1', status: 'online' }
  const target = { id: 'ssh-ui-target', name: '测试开发机 · codex', path: '/tmp/demo/.codex/skills', connectionId: connection.id, transport: 'ssh' }
  const plan = { id: 'preview-ui', workspace: '/workspace', requiresOverwrite: true, targets: [{ target, skills: [{ name: 'demo-skill', status: 'modified', files: [{ path: 'SKILL.md', change: 'modified' }] }] }] }
  let connections = [], targets = [], observations = [], runs = [], checks = 0
  let executed = false, inventoryReads = 0
  await page.route('**/api/targets/*/inventory', async route => {
    inventoryReads++
    expect(targets).toHaveLength(1)
    await route.fulfill({ json: { exists: true, skills: [{ name: 'demo-skill' }, { name: 'remote-only' }], skipped: [], truncated: false, observedAt: '2026-09-08T00:00:00Z' } })
  })
  await page.route('**/api/connections**', async route => {
    const url = new URL(route.request().url())
    let data
    if (url.pathname.endsWith('/check')) data = connection
    else if (url.pathname.endsWith('/discover-targets')) data = { targets: [{ path: target.path, agentKind: 'codex', scope: 'global' }] }
    else if (route.request().method() === 'POST') {
      expect(route.request().postDataJSON().host).toBe('dev1')
      connections = [connection]; data = connection
    } else data = connections
    await route.fulfill({ json: data })
  })
  await page.route('**/api/targets', async route => {
    if (route.request().method() === 'POST') {
      expect(route.request().postDataJSON().connectionId).toBe(connection.id)
      targets = [target]
      await route.fulfill({ json: target })
    } else await route.fulfill({ json: targets })
  })
  await page.route('**/api/sync/observations', route => route.fulfill({ json: observations }))
  await page.route('**/api/sync/preview', async route => {
    expect(route.request().postDataJSON()).toEqual({ targetIds: [target.id], skills: ['demo-skill'] })
    await route.fulfill({ json: plan })
  })
  await page.route('**/api/sync/runs**', async route => {
    if (route.request().method() === 'POST') {
      expect(route.request().postDataJSON()).toEqual({ previewId: plan.id, force: true })
      executed = true
      runs = [{ id: 'run-ui', state: 'running', workspace: '/workspace', createdAt: '2026-09-08T00:00:00Z', progress: { completed: 0, total: 1 }, results: [{ target, state: 'running', skills: [{ name: 'demo-skill', state: 'running' }] }] }]
      await route.fulfill({ json: runs[0] })
    } else if (new URL(route.request().url()).pathname.endsWith('/run-ui')) {
      checks++
      const run = { ...runs[0], state: 'succeeded', progress: { completed: 1, total: 1 }, results: [{ target, state: 'succeeded', skills: [{ name: 'demo-skill', state: 'succeeded' }] }] }
      runs = [run]
      observations = [{ targetId: target.id, observedAt: '2026-09-08T00:00:01Z', skills: [{ status: 'synced' }] }]
      await route.fulfill({ json: run })
    } else await route.fulfill({ json: runs })
  })

  await page.goto('/ssh')
  await expect(page.getByRole('heading', { name: '连接你的开发机' })).toBeVisible()
  await page.getByRole('button', { name: '添加第一个连接' }).click()
  await page.getByLabel('连接名称').fill(connection.name)
  await page.getByLabel('SSH Host', { exact: true }).fill(connection.host)
  await page.getByRole('button', { name: '保存并检查' }).click()
  await page.getByRole('button', { name: '添加目标', exact: true }).first().click()
  await page.getByRole('button', { name: '发现 Agent 目录' }).click()
  await page.locator('.ssh-target-options .q-checkbox').click()
  await page.locator('.qqx-modal').getByRole('button', { name: '添加目标', exact: true }).click()
  await expect(page.locator('.remote-inventory')).toContainText('remote-only')
  expect(inventoryReads).toBe(1)
  await page.getByRole('button', { name: '从 workspace 安装', exact: true }).click()
  await page.getByLabel('搜索 Skill').fill('demo-skill')
  await page.locator('.ssh-skill-list .q-checkbox').filter({ hasText: /^demo-skill[^-]/ }).click()
  await page.getByRole('button', { name: '检查状态并预览' }).click()
  await expect(page.getByRole('heading', { name: '确认同步内容' })).toBeVisible()
  const execute = page.getByRole('button', { name: '执行同步', exact: true })
  await expect(execute).toBeDisabled()
  expect(executed).toBe(false)
  await page.getByText('demo-skill', { exact: true }).last().click()
  await expect(page.locator('.ssh-diff-row')).toContainText('SKILL.md')
  await page.getByText('确认覆盖以上有差异的 Skill 内容，包括目标中额外的文件').click()
  await expect(execute).toBeEnabled()
  await page.screenshot({ path: testInfo.outputPath('preview-desktop.png'), fullPage: true, animations: 'disabled' })
  await execute.click()
  await expect(page.getByRole('heading', { name: '同步执行记录' })).toBeVisible()
  await expect(page.locator('.qqx-modal').getByText('1 / 1 项')).toBeVisible()
  expect(checks).toBeGreaterThan(0)
  await page.getByRole('button', { name: '关闭', exact: true }).last().click()
  await expect(page.getByRole('heading', { name: '同步执行记录' })).toBeHidden()
  await page.getByRole('button', { name: '设置', exact: true }).click()
  await expect(page.locator('.ssh-target-row')).toContainText('1 已同步')
  await page.getByRole('button', { name: '完成', exact: true }).click()
  await page.screenshot({ path: testInfo.outputPath('synced-desktop.png'), fullPage: true, animations: 'disabled' })
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.locator('.ssh-page')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({ path: testInfo.outputPath('synced-mobile.png'), fullPage: true, animations: 'disabled' })
})
