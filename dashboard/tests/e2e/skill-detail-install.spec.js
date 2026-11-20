import { expect, test } from '@playwright/test'

test('skill detail installs using stable target ID, surfaces errors in both tabs, expands project agent dirs, and handles mid-flight close', async ({ page }) => {
  const targetA = { id: 'target-uuid-1', name: 'my-claude', label: 'my-claude', path: '/mock/home/.claude/skills' }
  const targetB = { id: 'target-uuid-2', name: 'my-codex', label: 'my-codex', path: '/mock/home/.codex/skills' }
  const projectRoot = '/mock/work/demo-app'
  const projectAgentClaude = '/mock/work/demo-app/.claude/skills'
  const projectAgentCodex = '/mock/work/demo-app/.codex/skills'

  const statusByTarget = {
    [targetA.path]: 'missing',
    [targetB.path]: 'missing',
    [projectAgentClaude]: 'missing',
    [projectAgentCodex]: 'missing',
  }
  const executedTargets = []
  let releaseDelayed
  const delayedInstall = new Promise(resolve => { releaseDelayed = resolve })

  await page.route('**/api/sync/config', route => route.fulfill({
    json: { schema_version: 2, targets: [targetA, targetB] },
  }))
  await page.route('**/api/sync/status**', route => {
    const rows = [
      { target: targetA.path, name: 'demo-skill', status: statusByTarget[targetA.path] },
      { target: targetB.path, name: 'demo-skill', status: statusByTarget[targetB.path] },
      { target: projectAgentClaude, name: 'demo-skill', status: statusByTarget[projectAgentClaude], _project: 'DemoApp', _projectId: 'proj-1', _projectRoot: projectRoot, _agent: 'claude' },
      { target: projectAgentCodex, name: 'demo-skill', status: statusByTarget[projectAgentCodex], _project: 'DemoApp', _projectId: 'proj-1', _projectRoot: projectRoot, _agent: 'codex' },
    ]
    return route.fulfill({ json: rows })
  })
  await page.route('**/api/sync/projects', route => route.fulfill({
    json: [{ id: 'proj-1', name: 'DemoApp', targets: [projectRoot] }],
  }))
  await page.route('**/api/sync/discover**', route => route.fulfill({
    json: {
      path: projectRoot,
      agent_dirs: [
        { agent: 'claude', path: projectAgentClaude },
        { agent: 'codex', path: projectAgentCodex },
      ],
    },
  }))
  await page.route('**/api/sync/execute', async route => {
    const body = route.request().postDataJSON()
    executedTargets.push(body.target)

    if (body.target === targetA.id) {
      statusByTarget[targetA.path] = 'synced'
      return route.fulfill({ json: { success: true, stdout: `Synced 1 skill(s) to ${targetA.path}`, stderr: '', syncedCount: 1 } })
    }
    if (body.target === targetB.id) {
      return route.fulfill({
        status: 400,
        json: { detail: { code: 'unsafe-path', message: `Symlink skill directories are not supported: ${targetB.path}/demo-skill` } },
      })
    }
    if (body.target === '/mock/noop') {
      return route.fulfill({ json: { success: true, stdout: 'No skills to sync (no matching skills in workspace: demo-skill)', stderr: '', syncedCount: 0 } })
    }
    if (body.target === '/mock/delayed') {
      await delayedInstall
      return route.fulfill({ json: { success: true, stdout: 'Synced 1 skill(s) to /mock/delayed', stderr: '', syncedCount: 1 } })
    }
    if (body.target === projectAgentClaude || body.target === projectAgentCodex) {
      statusByTarget[body.target] = 'synced'
      return route.fulfill({ json: { success: true, stdout: `Synced 1 skill(s) to ${body.target}`, stderr: '', syncedCount: 1 } })
    }
    return route.fulfill({ status: 400, json: { detail: { code: 'invalid', message: `Unexpected target: ${body.target}` } } })
  })

  const pageErrors = []
  page.on('pageerror', err => pageErrors.push(err.message))

  await page.goto('/skills')
  await page.getByRole('heading', { name: 'demo-skill', exact: true }).click()
  await page.getByRole('button', { name: '安装', exact: true }).click()

  // 1. Custom target name is preserved; clicking install sends stable ID (not display name) and updates to 已安装.
  const claudeRow = page.locator('.im-row').filter({ hasText: 'my-claude' })
  await expect(claudeRow).toBeVisible()
  await claudeRow.getByRole('button', { name: '安装', exact: true }).click()
  await expect(claudeRow.getByRole('button', { name: '已安装', exact: true })).toBeVisible()
  expect(executedTargets[0]).toBe(targetA.id)

  // 2. HTTP 200 zero-synced no-op in custom path surfaces an error instead of false success.
  await page.locator('.im-custom-input').fill('/mock/noop')
  await page.locator('.im-custom-row').getByRole('button', { name: '安装', exact: true }).click()
  await expect(page.locator('.im-error')).toContainText('No skills to sync')

  // 3. Project group "一键安装到全部目标" installs into discovered agent dirs, NOT project root.
  await page.getByRole('button', { name: '项目组', exact: true }).click()
  await page.locator('.im-project-header').filter({ hasText: 'DemoApp' }).click()
  await expect(page.locator('.im-agent-row')).toHaveCount(2)
  await page.getByRole('button', { name: '一键安装到全部目标', exact: true }).click()
  await expect(page.locator('.im-agent-row').first().getByRole('button', { name: '已安装', exact: true })).toBeVisible()
  await expect(page.locator('.im-agent-row').nth(1).getByRole('button', { name: '已安装', exact: true })).toBeVisible()
  expect(executedTargets).toContain(projectAgentClaude)
  expect(executedTargets).toContain(projectAgentCodex)
  expect(executedTargets).not.toContain(projectRoot)

  // 4. Sync Status tab renders clear error alerts when target fails with unsafe-path.
  await page.getByRole('button', { name: '同步状态', exact: true }).click()
  const codexCard = page.locator('.sync-card').filter({ hasText: 'my-codex' })
  await expect(codexCard).toBeVisible()
  await codexCard.getByRole('button', { name: '同步', exact: true }).click()
  await expect(page.locator('.sync-list .im-error')).toContainText('符号链接')
  await expect(page.locator('.sync-list .im-error')).toContainText('demo-skill')

  // 5. Closing the modal while an install is in flight does not throw a pageerror.
  await page.getByRole('button', { name: '安装', exact: true }).click()
  await page.locator('.im-custom-input').fill('/mock/delayed')
  await page.locator('.im-custom-row').getByRole('button', { name: '安装', exact: true }).click()
  await page.keyboard.press('Escape')
  releaseDelayed()
  await page.waitForTimeout(300)
  expect(pageErrors).toEqual([])
})
