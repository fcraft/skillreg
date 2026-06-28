import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30_000,
  use: {
    baseURL: 'http://127.0.0.1:8765',
    headless: true,
  },
  webServer: {
    command: 'bash -lc ".venv/bin/python tests/e2e/serve_dashboard.py"',
    cwd: '..',
    url: 'http://127.0.0.1:8765/api/health',
    reuseExistingServer: true,
    timeout: 60_000,
  },
})
