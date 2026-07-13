import { test, expect } from '@playwright/test'
import fs from 'node:fs'

/**
 * Browser acceptance test for the V5 preview + export flow (KAN-148) — the last
 * rung of L3 acceptance for Ratio.
 *
 * Drives the Svelte SPA in a headless browser against the live FastAPI engine:
 * generate a card, Approve it (it lands in the WorksheetTray), then exercise the
 * three export actions. Export routes render HTML → headless Chromium → PDF
 * (ADR-0008), so this needs the real API with a Chromium browser (installed in
 * the e2e job). Mirrors the harness of worksheet.spec.js + generate.spec.js.
 */

// Approve one generated card so the worksheet tray has an item to export.
async function approveOne(page) {
  const generate = page.getByRole('button', { name: 'Generate', exact: true })
  await expect(generate).toBeVisible()
  await generate.click()

  const card = page.locator('article.card').first()
  await expect(card).toBeVisible()
  await card.getByRole('button', { name: 'Approve' }).click()

  const tray = page.locator('aside.tray')
  await expect(tray.locator('ol.items > li.item')).toHaveCount(1)
  return tray
}

test('Export worksheet PDF downloads a non-empty .pdf', async ({ page }) => {
  await page.goto('/')
  const tray = await approveOne(page)

  const button = page.getByRole('button', { name: 'Export worksheet PDF' })
  await expect(button).toBeEnabled()

  const [download] = await Promise.all([
    page.waitForEvent('download'),
    button.click(),
  ])

  const filename = download.suggestedFilename()
  expect(filename).toMatch(/\.pdf$/)
  expect(filename).not.toMatch(/-answers\.pdf$/)

  const path = await download.path()
  expect(path).toBeTruthy()
  const bytes = fs.readFileSync(path)
  expect(bytes.length).toBeGreaterThan(0)
  // A real PDF begins with the %PDF magic bytes.
  expect(bytes.subarray(0, 4).toString('latin1')).toBe('%PDF')

  // Sanity: the tray still holds the approved item after the download.
  await expect(tray.locator('ol.items > li.item')).toHaveCount(1)
})

test('Export answer-key PDF downloads a non-empty -answers.pdf', async ({ page }) => {
  await page.goto('/')
  await approveOne(page)

  const button = page.getByRole('button', { name: 'Export answer-key PDF' })
  await expect(button).toBeEnabled()

  const [download] = await Promise.all([
    page.waitForEvent('download'),
    button.click(),
  ])

  const filename = download.suggestedFilename()
  expect(filename).toMatch(/-answers\.pdf$/)

  const path = await download.path()
  expect(path).toBeTruthy()
  const bytes = fs.readFileSync(path)
  expect(bytes.length).toBeGreaterThan(0)
  expect(bytes.subarray(0, 4).toString('latin1')).toBe('%PDF')
})

test('Preview opens a new tab showing the rendered worksheet', async ({ page }) => {
  await page.goto('/')
  await approveOne(page)

  const button = page.getByRole('button', { name: 'Preview', exact: true })
  await expect(button).toBeEnabled()

  const [popup] = await Promise.all([
    page.waitForEvent('popup'),
    button.click(),
  ])

  // The preview is the exact print document: a worksheet sheet with a title and
  // at least one question.
  await expect(popup.locator('main.sheet.worksheet')).toBeVisible()
  await expect(popup.locator('.sheet-title')).toBeVisible()
  await expect(popup.locator('li.question').first()).toBeVisible()
})
