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
  await expect(page.locator('.skill-list-row').filter({ hasText: 'demo-skill' })).toBeVisible()

  await page.getByRole('link', { name: '项目组' }).click()
  await page.waitForURL('**/projects')
  await expect(page.getByRole('heading', { name: '项目组管理' })).toBeVisible()
  await expect(page.getByText('暂无项目组')).toBeVisible()
})

test('spa fallback supports direct route entry', async ({ page }) => {
  await page.goto('/sync')
  await expect(page.getByRole('heading', { name: 'Sync 工具' })).toBeVisible()
  await expect(page.getByText('demo-skill')).toBeVisible()
})
