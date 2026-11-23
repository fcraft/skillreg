import { spawn } from 'node:child_process'
import { once } from 'node:events'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { createInterface } from 'node:readline'
import { fileURLToPath } from 'node:url'
import { expect, test as base } from '@playwright/test'

const root = fileURLToPath(new URL('../../../', import.meta.url))
const test = base.extend({
  firstVisitUrl: async ({}, use) => {
    const home = await mkdtemp(path.join(tmpdir(), 'skillreg-first-visit-'))
    const server = spawn(path.join(root, '.venv/bin/python'), ['tests/e2e/serve_dashboard.py', '--first-visit'], {
      cwd: root, env: { HOME: home, PATH: '/usr/bin:/bin' }, stdio: ['ignore', 'pipe', 'inherit'],
    })
    const exited = once(server, 'exit')
    try {
      const lines = createInterface({ input: server.stdout })
      const url = await lines[Symbol.asyncIterator]().next()
      expect(url.value).toMatch(/^http:\/\/127\.0\.0\.1:\d+$/)
      await use(url.value)
    } finally {
      server.kill()
      await exited
      await rm(home, { recursive: true, force: true })
    }
  },
})

for (const theme of ['light', 'dark']) {
  test(`first visit and manual additions persist in ${theme} mode`, async ({ page, firstVisitUrl }) => {
    const errors = []
    page.on('pageerror', err => errors.push(err.message))
    page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()) })
    await page.addInitScript(value => localStorage.setItem('qqx-theme', value), theme)
    await page.goto(firstVisitUrl)
    const dialog = page.getByRole('dialog', { name: '选择要同步到的 Agent' })
    await expect(dialog).toBeVisible()
    await expect(page.locator('html')).toHaveAttribute('data-theme', theme)
    if (theme === 'light') {
      await dialog.getByRole('checkbox', { name: /Claude/ }).check()
      await dialog.getByRole('checkbox', { name: /Cursor/ }).check()
      await dialog.getByRole('button', { name: /加入所选/ }).click()
    } else {
      await dialog.getByRole('button', { name: '稍后再说' }).click()
    }
    await expect(dialog).toBeHidden()
    await page.goto(firstVisitUrl + '/sync')
    await expect(page.getByRole('button', { name: '发现本机 Agent' }).first()).toBeVisible()
    await expect(dialog).toBeHidden()
    await expect(page.locator('.target-tab')).toHaveCount(theme === 'light' ? 2 : 0)
    await page.getByRole('button', { name: '发现本机 Agent' }).first().click()
    const picker = page.getByRole('dialog', { name: '添加内置 Agent' })
    await picker.getByRole('searchbox').fill('opencode')
    await picker.getByRole('button', { name: '加入', exact: true }).click()
    await expect(page.locator('.target-tab').filter({ hasText: 'OpenCode' })).toBeVisible()
    await page.goto(firstVisitUrl + '/skills')
    await page.getByRole('heading', { name: 'demo-skill', exact: true }).click()
    await page.getByRole('button', { name: '安装', exact: true }).click()
    await page.getByRole('button', { name: '添加内置 Agent' }).click()
    await picker.getByRole('searchbox').fill('gemini')
    await picker.getByRole('checkbox', { name: /Gemini CLI/ }).check()
    await picker.getByRole('button', { name: /加入所选/ }).click()
    await expect(page.locator('.im-row').filter({ hasText: 'Gemini CLI' })).toBeVisible()
    expect(errors).toEqual([])
  })
}
