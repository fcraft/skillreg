import { defineConfig } from '@playwright/test'

const baseURL = `http://127.0.0.1:${process.env.SKILLREG_E2E_PORT || 8765}`

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30_000,
  use: {
    baseURL,
    headless: true,
  },
  webServer: {
    command: 'bash -lc ".venv/bin/python tests/e2e/serve_dashboard.py"',
    cwd: '..',
    url: baseURL + '/api/health',
    reuseExistingServer: true,
    timeout: 60_000,
  },
})
