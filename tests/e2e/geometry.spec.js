import { test, expect } from '@playwright/test'

/**
 * Browser acceptance test for the live topic × difficulty selector driving a
 * geometry question (KAN-151 + KAN-231).
 *
 * Selects Geometry (Area & Perimeter) / Hard, clicks Generate (which calls the
 * live FastAPI engine → geometry_area_hard), and asserts the acceptance surface
 * for a mandatory-figure card: the geometry figure renders as an inline SVG, and
 * there is NO toggle-diagram control (the engine omits it from available_ops).
 */
test('selecting a geometry topic renders a mandatory figure with no toggle', async ({ page }) => {
  await page.goto('/')

  // Drive the live selectors.
  await page.getByLabel('Topic').selectOption('geometry_area')
  await page.getByLabel('Difficulty').selectOption('hard')

  await page.getByRole('button', { name: 'Generate' }).click()

  // Auto-wait for the first card to render (the API round-trip drives this).
  const card = page.locator('article.card').first()
  await expect(card).toBeVisible()

  // Validation badge must read "pass".
  await expect(card.locator('.badge.pass')).toHaveText('pass')

  // The blueprint code confirms the selector built geometry_area_hard.
  await expect(card.locator('.meta')).toContainText('geometry_area_hard')

  // The geometry figure renders as an inline SVG.
  const svg = card.locator('.diagram svg')
  await expect(svg).toBeVisible()

  // Mandatory figure → no Show/Hide diagram control anywhere on the card.
  await expect(card.getByRole('button', { name: /diagram/i })).toHaveCount(0)
})
