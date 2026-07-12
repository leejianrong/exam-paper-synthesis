import { defineConfig, devices } from '@playwright/test'

// Ports for the two dev servers Playwright boots for the e2e run.
const API_PORT = 8000
const WEB_PORT = 5173

/**
 * Playwright config for the Generate-flow browser acceptance test (ADR-0008).
 *
 * `webServer` boots BOTH backends for the run: the FastAPI engine (:8000) and
 * the Vite dev server for the Svelte SPA (:5173). Locally we reuse an already
 * running server; in CI we always start fresh.
 */
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? [['github'], ['list']] : 'list',
  timeout: 30_000,
  expect: { timeout: 10_000 },

  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    trace: 'on-first-retry',
  },

  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],

  webServer: [
    {
      // FastAPI engine that serves POST /generate (ratio_medium questions).
      command: `uv run uvicorn app.main:app --app-dir api --port ${API_PORT}`,
      url: `http://localhost:${API_PORT}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      stdout: 'pipe',
      stderr: 'pipe',
    },
    {
      // Vite dev server for the Svelte SPA (reads VITE_API, defaults to :8000).
      command: 'npm --prefix web run dev',
      url: `http://localhost:${WEB_PORT}`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      stdout: 'pipe',
      stderr: 'pipe',
    },
  ],
})
