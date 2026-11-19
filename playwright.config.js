import { defineConfig, devices } from '@playwright/test'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { API_PORT, CSP_PORT, E2E_SUFFIX, PORTS_OVERRIDDEN, WEB_PORT } from './tests/e2e/ports.js'

// Ports for the servers Playwright boots for the e2e run: the API, the Vite dev server, and a
// production-shaped server for the CSP spec (the built SPA served by the API on ONE origin).
// E2E_API_PORT / E2E_WEB_PORT / E2E_CSP_PORT move them off the usual dev ports, so an e2e run
// can sit beside a developer's own servers (tests/e2e/ports.js gives the specs the same ports).
// With a port moved, never reuse a server already listening: it would be someone else's.
const REUSE = !process.env.CI && !PORTS_OVERRIDDEN
const CSP_DIST = path.join(os.tmpdir(), `exam-e2e-web-dist${E2E_SUFFIX}`)

// The document API (W1b) is tenant-scoped; the e2e run uses the dev identity stub and a
// throwaway database (specs create their own papers and never assume an empty store).
const DOCS_DB = path.join(os.tmpdir(), `exam-e2e-documents${E2E_SUFFIX}.sqlite3`)
// The question bank the API reads (the CLI writes the same file, as the `local` owner).
const BANK_DB = path.join(os.tmpdir(), `exam-e2e-bank${E2E_SUFFIX}.sqlite3`)
const ASSETS_DB = path.join(os.tmpdir(), `exam-e2e-assets${E2E_SUFFIX}.sqlite3`)
const AUTH_DB = path.join(os.tmpdir(), `exam-e2e-accounts${E2E_SUFFIX}.sqlite3`)
const USAGE_DB = path.join(os.tmpdir(), `exam-e2e-usage${E2E_SUFFIX}.sqlite3`)

/**
 * Playwright config for the Generate-flow browser acceptance test (ADR-0008).
 *
 * `webServer` boots BOTH backends for the run: the FastAPI engine (:8000) and
 * the Vite dev server for the Svelte SPA (:5173). Locally we reuse an already
 * running server on those ports; in CI, or when E2E_*_PORT moves a port, we always
 * start fresh.
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
      reuseExistingServer: REUSE,
      timeout: 120_000,
      stdout: 'pipe',
      stderr: 'pipe',
      // A server that is already running locally is reused as-is, so the editor spec
      // needs one started with these three variables (CI always starts fresh).
      env: { ...process.env, EXAM_DEV_AUTH: '1', EXAM_DOCS_PATH: DOCS_DB, EXAM_BANK_PATH: BANK_DB, EXAM_ASSETS_PATH: ASSETS_DB,
        EXAM_AUTH_PATH: AUTH_DB,
        // the SPA's origin: CORS allows it and sign-in redirects back to it
        EXAM_WEB_URL: `http://localhost:${WEB_PORT}`,
        EXAM_USAGE_PATH: USAGE_DB,
        // e2e exports freely (the allowance is covered by pytest and vitest)
        EXAM_EXPORT_LIMIT_PER_DAY: '0',
        EXAM_EXPORT_LIMIT_PER_MINUTE: '0',
      },
    },
    {
      // Built SPA + API on one origin, as in production (the Dockerfile builds with VITE_API="").
      // Only tests/e2e/csp.spec.js uses it: the Content-Security-Policy is enforced here.
      command:
        `env VITE_API= npm --prefix web run build -- --outDir ${CSP_DIST} --emptyOutDir && ` +
        `uv run uvicorn app.main:app --app-dir api --port ${CSP_PORT}`,
      url: `http://localhost:${CSP_PORT}/health`,
      reuseExistingServer: REUSE,
      timeout: 240_000,
      stdout: 'pipe',
      stderr: 'pipe',
      env: { ...process.env, EXAM_DEV_AUTH: '1', EXAM_WEB_DIST: CSP_DIST, EXAM_DOCS_PATH: DOCS_DB, EXAM_BANK_PATH: BANK_DB, EXAM_ASSETS_PATH: ASSETS_DB,
        EXAM_AUTH_PATH: AUTH_DB, EXAM_USAGE_PATH: USAGE_DB,
        EXAM_EXPORT_LIMIT_PER_DAY: '0', EXAM_EXPORT_LIMIT_PER_MINUTE: '0' },
    },
    {
      // Vite dev server for the Svelte SPA, pointed at the e2e API.
      command: `npm --prefix web run dev -- --port ${WEB_PORT} --strictPort`,
      url: `http://localhost:${WEB_PORT}`,
      reuseExistingServer: REUSE,
      timeout: 120_000,
      stdout: 'pipe',
      stderr: 'pipe',
      env: { ...process.env, VITE_API: `http://localhost:${API_PORT}` },
    },
  ],
})
