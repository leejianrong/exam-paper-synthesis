import { test, expect } from '@playwright/test'
import { openClassic } from './helpers.js'

/**
 * Browser acceptance test for the live topic × difficulty selector driving a
 * geometry question (KAN-151 + KAN-231).
 *
 * Selects Geometry (Area & Perimeter) / Hard, clicks Generate (which calls the
 * live FastAPI engine → geometry_area_hard), and asserts the acceptance surface
 * for a mandatory-figure card: the geometry figure is fetched from the engine
 * (POST /render/diagram, EXA-151) and shows as an inline SVG, and
 * there is NO toggle-diagram control (the engine omits it from available_ops).
 */
test('selecting a geometry topic renders a mandatory figure with no toggle', async ({ page }) => {
  await openClassic(page)

  // Drive the live selectors.
  await page.getByLabel('Topic').selectOption('geometry_area')
  await page.getByLabel('Difficulty').selectOption('hard')

  // The figure is drawn by the engine, not the browser (EXA-151).
  const drawn = page.waitForResponse(
    (r) => r.url().endsWith('/render/diagram') && r.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Generate' }).click()
  const drawnResp = await drawn
  expect(drawnResp.ok()).toBe(true)
  expect(JSON.parse(drawnResp.request().postData() ?? '{}').diagram.type).toBe('geometry_figure')

  // Auto-wait for the first card to render (the API round-trip drives this).
  const card = page.locator('article.card').first()
  await expect(card).toBeVisible()

  // Validation badge must read "pass".
  await expect(card.locator('.badge.pass')).toHaveText('pass')

  // The blueprint code confirms the selector built geometry_area_hard.
  await expect(card.locator('.meta')).toContainText('geometry_area_hard')

  // The geometry figure shows as the engine's inline SVG.
  const svg = card.locator('[aria-label="geometry figure"] svg')
  await expect(svg).toBeVisible()

  // Mandatory figure → no Show/Hide diagram control anywhere on the card.
  await expect(card.getByRole('button', { name: /diagram|model (in|from) key/i })).toHaveCount(0)
})
