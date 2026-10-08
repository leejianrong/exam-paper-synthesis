import { test, expect } from '@playwright/test'
import fs from 'node:fs'

/**
 * The Content-Security-Policy is real and nothing the app needs is blocked by it.
 *
 * Runs against the production-shaped server (built SPA + API on one origin, :8001), because the
 * policy comes from the API: the Vite dev server (:5173) never sends it. Every `securitypolicy-
 * violation` in every frame (the preview iframe included) fails the test.
 */
const ORIGIN = 'http://localhost:8001'

async function collectViolations(page) {
  await page.addInitScript(() => {
    window.__csp = window.__csp || []
    document.addEventListener('securitypolicyviolation', (e) =>
      window.__csp.push(`${e.violatedDirective} ${e.blockedURI} ${e.sample ?? ''}`),
    )
  })
  const consoleRefusals = []
  page.on('console', (m) => {
    if (/Content Security Policy|Refused to/i.test(m.text())) consoleRefusals.push(m.text())
  })
  return async () => {
    const found = [...consoleRefusals]
    for (const frame of page.frames()) {
      found.push(...((await frame.evaluate(() => window.__csp ?? []).catch(() => [])) ?? []))
    }
    return found
  }
}

test('the app sends an enforcing policy with no unsafe script sources', async ({ request }) => {
  const res = await request.get(`${ORIGIN}/`)
  const csp = res.headers()['content-security-policy']
  expect(csp).toContain("object-src 'none'")
  const script = csp.split('; ').find((d) => d.startsWith('script-src '))
  expect(script).not.toContain('unsafe')
  expect(await res.text()).not.toMatch(/<script(?![^>]*\bsrc=)[^>]*>\s*\S/) // no inline scripts
})

test('editor, KaTeX preview, PDF export and the classic tray work under the policy', async ({ page }) => {
  const violations = await collectViolations(page)

  await page.goto(`${ORIGIN}/#/`)
  await page.getByRole('button', { name: '+ New paper' }).click()
  await expect(page.getByLabel('Paper title')).toBeVisible()

  await page.getByRole('button', { name: 'Add question' }).click()
  const dialog = page.getByRole('dialog', { name: 'Add question' })
  await dialog.getByLabel('Topic').selectOption({ label: 'Fractions' })
  await dialog.getByRole('button', { name: /^Generate/ }).click()
  await expect(dialog.getByTestId('candidate')).toHaveCount(3)
  await dialog.getByRole('button', { name: 'Use this' }).first().click()
  await expect(page.getByTestId('question-block')).toHaveCount(1)

  // In-editor preview: a srcdoc iframe inheriting the policy; KaTeX must have run in it.
  await page.getByRole('button', { name: 'Preview' }).click()
  const frame = page.frameLocator('iframe[title="Print preview"]')
  await expect(frame.locator('html[data-katex-rendered="true"]')).toBeAttached()
  // all three hashed inline scripts executed: KaTeX itself is loaded in the frame
  expect(await frame.locator('html').evaluate(() => typeof window.katex?.renderToString)).toBe('function')
  await page.getByRole('button', { name: 'Close preview' }).click()

  // PDF export (Chromium renders it server-side; the download must still arrive).
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'Student PDF' }).click(),
  ])
  const bytes = fs.readFileSync(await download.path())
  expect(bytes.subarray(0, 4).toString('latin1')).toBe('%PDF')

  // Classic page: Preview opens the print HTML as a blob: tab, which inherits the policy.
  await page.goto(`${ORIGIN}/#/classic`)
  await page.getByRole('button', { name: 'Generate', exact: true }).click()
  await page.locator('article.card').first().getByRole('button', { name: 'Approve' }).click()
  const [popup] = await Promise.all([
    page.waitForEvent('popup'),
    page.getByRole('button', { name: 'Preview', exact: true }).click(),
  ])
  await expect(popup.locator('html[data-katex-rendered="true"]')).toBeAttached()

  expect(await violations()).toEqual([])
  expect(await (async () => {
    const out = []
    for (const f of popup.frames()) out.push(...(await f.evaluate(() => window.__csp ?? []).catch(() => [])))
    return out
  })()).toEqual([])
})
