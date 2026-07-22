import { expect, test } from '@playwright/test'
import path from 'node:path'

test('first run guides workspace creation into the first skill import', async ({ page }) => {
  await page.route('**/api/workspace/current', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ workspace_path: null, resolved_path: null, configured: false }),
    })
  })
  await page.route('**/api/workspace/create', async (route) => {
    expect(route.request().postDataJSON()).toEqual({ path: '~/guided-skills' })
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        workspace_path: '/Users/demo/guided-skills',
        initial_commit: 'abc1234',
        remote_configured: false,
      }),
    })
  })

  await page.goto('/')
  await expect(page.getByRole('heading', { name: '准备你的 Skill Workspace' })).toBeVisible()
  await expect(page.getByText('不会配置远端或自动 push')).toBeVisible()

  await page.getByRole('textbox').fill('~/guided-skills')
  await page.getByRole('button', { name: '创建并继续' }).click()

  await expect(page.getByRole('heading', { name: 'Workspace 已就绪' })).toBeVisible()
  await expect(page.getByText('abc1234')).toBeVisible()
  await expect(page.getByText('尚未配置')).toBeVisible()

  await page.getByRole('button', { name: /导入首个 Skill/ }).click()
  await expect(page.getByRole('heading', { name: '导入新技能' })).toBeVisible()
})

test('first run can select an existing workspace and open target setup', async ({ page }) => {
  await page.route('**/api/workspace/current', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ workspace_path: null, resolved_path: null, configured: false }),
    })
  })
  await page.route('**/api/workspace/switch', async (route) => {
    expect(route.request().postDataJSON()).toEqual({ path: '~/existing-skills' })
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true, workspace_path: '/Users/demo/existing-skills' }),
    })
  })

  await page.goto('/')
  await page.getByRole('button', { name: '使用已有的' }).click()
  await page.getByRole('textbox').fill('~/existing-skills')
  await page.getByRole('button', { name: '选择并继续' }).click()

  await expect(page.getByText('使用已有目录')).toBeVisible()
  await expect(page.getByText('尚未配置')).toHaveCount(0)
  await page.getByRole('button', { name: /添加同步目标/ }).click()
  await expect(page.getByRole('heading', { name: '新增目标目录' })).toBeVisible()
})

test('switching to a missing workspace asks before creating it', async ({ page }) => {
  const missingPath = '/tmp/skillreg-new-workspace'
  let createdPath = null

  await page.route('**/api/workspace/switch', async (route) => {
    await route.fulfill({
      status: 404,
      contentType: 'application/json',
      body: JSON.stringify({
        detail: {
          code: 'workspace_not_found',
          message: `Workspace does not exist: ${missingPath}`,
        },
      }),
    })
  })
  await page.route('**/api/workspace/create', async (route) => {
    createdPath = route.request().postDataJSON().path
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        workspace_path: missingPath,
        initial_commit: 'def5678',
        remote_configured: false,
      }),
    })
  })

  await page.goto('/')
  await page.getByRole('button', { name: /Workspace/ }).click()
  await page.locator('.workspace-modal-body input').fill(missingPath)
  await page.getByRole('button', { name: '确认切换' }).click()

  await expect(page.getByRole('heading', { name: '创建新 Workspace' })).toBeVisible()
  await expect(page.getByText(missingPath, { exact: true })).toBeVisible()
  await expect(page.getByText('Bad Request')).toHaveCount(0)
  expect(createdPath).toBeNull()

  await page.getByRole('button', { name: '确认创建' }).click()
  await expect.poll(() => createdPath).toBe(missingPath)
})

test('workspace switch can use the native folder picker', async ({ page }) => {
  const selectedPath = '/tmp/selected-skill-workspace'
  let switchedPath = null

  await page.route('**/api/workspace/select-directory', async (route) => {
    expect(route.request().postDataJSON().initialPath).toContain('/workspace')
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true, cancelled: false, path: selectedPath }),
    })
  })
  await page.route('**/api/workspace/switch', async (route) => {
    switchedPath = route.request().postDataJSON().path
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true, workspace_path: selectedPath }),
    })
  })

  await page.goto('/')
  await page.locator('.workspace-chip').click()
  await page.getByRole('button', { name: '选择文件夹' }).click()

  await expect(page.locator('.workspace-modal-body input')).toHaveValue(selectedPath)
  expect(switchedPath).toBeNull()

  await page.getByRole('button', { name: '确认切换' }).click()
  await expect.poll(() => switchedPath).toBe(selectedPath)
})

test('local folder import opens a folder picker and validates the selection', async ({ page }) => {
  await page.goto('/')
  await page.waitForURL('**/skills')
  await page.getByRole('button', { name: '导入', exact: true }).click()

  const folderInput = page.locator('input[webkitdirectory]')
  await expect(page.getByRole('button', { name: '选择文件夹' })).toBeVisible()
  await expect(folderInput).toHaveAttribute('multiple', '')

  await folderInput.setInputFiles(path.resolve('tests/fixtures/folder-picker-skill'))

  await expect(page.getByRole('heading', { name: '验证来源' })).toBeVisible()
  await expect(page.locator('.result-name')).toHaveText('folder-picker-skill')
  await expect(page.locator('.result-meta')).toHaveText('2 个文件')
})

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
  expect(panelBox.height).toBeLessThanOrEqual(643.1)
})
