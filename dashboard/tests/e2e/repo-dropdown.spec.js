import { expect, test } from '@playwright/test'

test('repository menu is teleported outside the clipped card', async ({ page }) => {
  await page.route('**/api/skills?full=1', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        skills: [],
        repoNodes: [],
        relationships: [],
        gitLogs: { main: [], submodules: {} },
        submodules: [{
          path: 'repos/example',
          description: 'Example repository',
          branch: 'main',
          remoteUrl: '',
          status: {
            isDetached: false,
            syncState: 'synced',
            indexAhead: 0,
            indexBehind: 0,
          },
        }],
      }),
    })
  })

  await page.goto('/repos')
  await page.getByTitle('管理仓库').click()

  const menu = page.locator('body > .repo-dropdown')
  await expect(menu).toBeVisible()
  await expect(menu).toHaveCSS('position', 'fixed')
  await expect(menu).toHaveCSS('z-index', '200')
  await expect(menu.getByRole('menuitem')).toHaveCount(3)
})
