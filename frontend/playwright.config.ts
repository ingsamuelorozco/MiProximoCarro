import { defineConfig, devices } from '@playwright/test'

const PYTHON = process.env.PYTHON || 'python'

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  use: { baseURL: 'http://127.0.0.1:8000', trace: 'retain-on-failure' },
  webServer: {
    command: `${PYTHON} -m uvicorn backend.app.main:app --port 8000`,
    cwd: '..',
    url: 'http://127.0.0.1:8000/api/salud',
    reuseExistingServer: true,
    env: { MIPROXIMOCARRO_TRM_OFFLINE: '1', MIPROXIMOCARRO_RATE_LIMIT: '10000/minute' },
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
