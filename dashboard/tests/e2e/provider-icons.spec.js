import { expect, test } from '@playwright/test'

for (const theme of ['light', 'dark']) {
  test(`provider icons render offline with unique gradient IDs in ${theme} mode`, async ({ page }) => {
    const targets = [
      { id: 'buddy-one', name: 'Buddy One', icon: 'codebuddy', path: '/mock/buddy-one' },
      { id: 'buddy-two', name: 'Buddy Two', icon: 'codebuddy', path: '/mock/buddy-two' },
      { id: 'workbuddy', name: 'WorkBuddy', icon: 'workbuddy', path: '/mock/workbuddy' },
      { id: 'custom', name: 'Custom Local', path: '/mock/custom' },
    ]
    const externalRequests = []
    page.on('request', request => {
      if (!request.url().startsWith('http://127.0.0.1:')) externalRequests.push(request.url())
    })
    await page.addInitScript(value => localStorage.setItem('qqx-theme', value), theme)
    await page.route('**/api/sync/config', route => route.fulfill({ json: { schema_version: 2, targets } }))
    await page.goto('/sync')
    await expect(page.locator('.target-tab [data-provider-icon="codebuddy"]')).toHaveCount(2)
    await expect(page.locator('.target-tab [data-provider-icon="custom"]')).toHaveCount(1)
    await expect(page.locator('html')).toHaveAttribute('data-theme', theme)

    const audit = await page.locator('.sr-provider-icon').evaluateAll(icons => {
      const ids = icons.flatMap(icon => [...icon.querySelectorAll('[id]')].map(node => node.id))
      const referencesResolveLocally = icons.every(icon => [...icon.querySelectorAll('[fill]')].every(node => {
        const match = node.getAttribute('fill').match(/^url\(#(.+)\)$/)
        return !match || [...icon.querySelectorAll('[id]')].some(def => def.id === match[1])
      }))
      return {
        ids,
        referencesResolveLocally,
        decorative: icons.every(icon => icon.getAttribute('aria-hidden') === 'true'),
        svgCount: icons.filter(icon => icon.querySelector('svg')).length,
        count: icons.length,
      }
    })
    expect(audit.ids.length).toBeGreaterThan(0)
    expect(new Set(audit.ids).size).toBe(audit.ids.length)
    expect(audit.referencesResolveLocally).toBe(true)
    expect(audit.decorative).toBe(true)
    expect(audit.svgCount).toBe(audit.count)
    expect(externalRequests).toEqual([])
  })
}
