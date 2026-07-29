import { expect, test } from '@playwright/test'

test('NPM source, managed repository, and Skill provide bidirectional navigation', async ({ page }) => {
  await page.goto('/sources?source=npm-design')

  const sourceCard = page.locator('[data-source-id="npm-design"]')
  await expect(sourceCard).toHaveClass(/source-card--selected/)
  await expect(sourceCard.getByText('@demo/npm-design', { exact: true })).toBeVisible()
  await sourceCard.getByRole('button', { name: 'npm-design →' }).click()

  await expect(page).toHaveURL(/\/repos\?repo=repos(?:%2F|\/)npm-design/)
  const repoCard = page.locator('[data-repository-path="repos/npm-design"]')
  await expect(repoCard).toHaveClass(/managed-repo-card--selected/)
  await expect(repoCard.getByText('NPM 托管')).toBeVisible()
  await repoCard.getByRole('button', { name: 'npm-design', exact: true }).click()

  const detail = page.locator('.detail-content')
  await expect(page.locator('.sdm-header-title')).toHaveText('npm-design')
  await expect(detail.getByRole('button', { name: '@demo/npm-design@1.2.3 →' })).toBeVisible()
  await expect(detail.getByRole('button', { name: 'npm-design →' })).toBeVisible()
  await detail.getByRole('button', { name: 'npm-design →' }).click()

  await expect(page).toHaveURL(/\/repos\?repo=repos(?:%2F|\/)npm-design/)
  await expect(repoCard).toHaveClass(/managed-repo-card--selected/)
  await repoCard.getByRole('button', { name: 'npm-design', exact: true }).click()
  await detail.getByRole('button', { name: '@demo/npm-design@1.2.3 →' }).click()

  await expect(page).toHaveURL(/\/sources\?source=npm-design/)
  await expect(page.locator('[data-source-id="npm-design"]')).toHaveClass(/source-card--selected/)

  await page.goto('/repos?repo=repos/submodule-design')
  const submoduleCard = page.locator('[data-repository-path="repos/submodule-design"]')
  await expect(submoduleCard).toHaveClass(/managed-repo-card--selected/)
  await expect(submoduleCard.getByText('NPM 托管')).toBeVisible()
  await page.reload()
  await expect(submoduleCard).toBeInViewport()
  await expect(submoduleCard).toHaveClass(/managed-repo-card--selected/)
})
