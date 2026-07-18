import { expect, test } from '@playwright/test'

test('dashboard routes and migration exclusions work', async ({ page }) => {
  await page.goto('/')
  await page.waitForURL('**/skills')

  await expect(page.getByRole('heading', { name: 'Agent Skills Dashboard' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Skills', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'demo-skill', exact: true })).toBeVisible()

  await expect(page.getByText('Hooks 管理')).toHaveCount(0)
  await expect(page.getByText('SSH 远程')).toHaveCount(0)

  await page.getByRole('link', { name: 'Sync 工具' }).click()
  await page.waitForURL('**/sync')
  await expect(page.getByRole('heading', { name: 'Sync 工具' })).toBeVisible()
  const demoSkillRow = page.locator('.skill-list-row').filter({
    has: page.locator('.skill-list-name', { hasText: /^demo-skill$/ }),
  })
  await expect(demoSkillRow).toBeVisible()

  await page.getByRole('link', { name: '项目组' }).click()
  await page.waitForURL('**/projects')
  await expect(page.getByRole('heading', { name: '项目组管理' })).toBeVisible()
  await expect(page.getByText('暂无项目组')).toBeVisible()
})

test('spa fallback supports direct route entry', async ({ page }) => {
  await page.goto('/sync')
  await expect(page.getByRole('heading', { name: 'Sync 工具' })).toBeVisible()
  await expect(page.getByText('demo-skill', { exact: true })).toBeVisible()
})

test('skill detail shows installed target state', async ({ page }) => {
  const syncResponse = await page.request.post('/api/sync/execute', {
    data: { target: 'claude-skills', skills: ['demo-skill'] },
  })
  expect(syncResponse.ok()).toBeTruthy()

  await page.goto('/')
  await page.waitForURL('**/skills')

  await page.getByRole('heading', { name: 'demo-skill', exact: true }).click()
  await page.getByRole('button', { name: '安装', exact: true }).click()

  const targetRow = page.locator('.im-row').filter({ hasText: 'claude-skills' })
  await expect(targetRow.getByRole('button', { name: '已安装', exact: true })).toBeVisible()
  await expect(targetRow.getByRole('button', { name: '安装', exact: true })).toHaveCount(0)
})

test('command panel ranks global results and supports keyboard navigation', async ({ page }) => {
  await page.goto('/')
  await page.waitForURL('**/skills')
  await expect(page.getByRole('heading', { name: 'demo-skill', exact: true })).toBeVisible()

  await page.keyboard.press('ControlOrMeta+K')
  const dialog = page.getByRole('dialog', { name: '全局搜索' })
  const search = dialog.getByRole('combobox', { name: '搜索 Skill、页面或操作' })
  await expect(dialog).toBeVisible()
  await expect(search).toBeFocused()

  const panelBox = await dialog.boundingBox()
  expect(panelBox?.width).toBeGreaterThanOrEqual(800)

  await search.fill('demo-skill')
  const results = dialog.getByRole('option')
  await expect(results.first().locator('.command-item-title')).toHaveText('demo-skill')
  await expect(results.first().locator('.command-kind')).toHaveText('Skill')

  await page.keyboard.press('ArrowDown')
  await expect(results.nth(1)).toHaveAttribute('aria-selected', 'true')
  await page.keyboard.press('Enter')
  await page.waitForURL('**/skills?skill=demo-skill-tools')
  await expect(dialog).toBeHidden()

  await page.keyboard.press('ControlOrMeta+K')
  await search.fill('同步')
  await expect(dialog.getByRole('option').first().locator('.command-item-title')).toHaveText('Sync 工具')

  await search.fill('mattpocock')
  await expect(dialog.getByRole('option').first().locator('.command-item-title')).toHaveText('ask-matt')

  await page.keyboard.press('Escape')
  await expect(dialog).toBeHidden()
})

test('command panel stays within a mobile viewport', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 })
  await page.goto('/')
  await page.waitForURL('**/skills')
  await expect(page.getByRole('heading', { name: 'demo-skill', exact: true })).toBeVisible()

  await page.keyboard.press('ControlOrMeta+K')
  const dialog = page.getByRole('dialog', { name: '全局搜索' })
  const panelBox = await dialog.boundingBox()

  expect(panelBox).not.toBeNull()
  expect(panelBox.x).toBeGreaterThanOrEqual(12)
  expect(panelBox.width).toBeLessThanOrEqual(351)
  expect(panelBox.height).toBeLessThanOrEqual(643)
})
