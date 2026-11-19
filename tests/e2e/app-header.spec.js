import { test, expect } from '@playwright/test'
import fs from 'node:fs'
import { API } from './ports.js'
import { newBlankPaper } from './helpers.js'

/**
 * EXA-167: one app header (Papers, Question bank, the avatar menu) on every screen but the
 * editor, and the question bank as its own page with Import.
 */

// A private owner per run, so the bank starts empty and the counts are exact.
const OWNER = `e2e-bank-page-${Date.now().toString(36)}`
test.use({ extraHTTPHeaders: { 'X-Dev-Owner': OWNER } })

test('the app header goes Papers → Question bank → Settings and back', async ({ page }) => {
  await page.goto('/')
  const nav = page.getByRole('navigation', { name: 'Main' })
  await expect(page.getByRole('heading', { name: 'Your papers' })).toBeVisible()
  await expect(nav.getByRole('link', { name: 'Papers' })).toHaveAttribute('aria-current', 'page')

  await nav.getByRole('link', { name: 'Question bank' }).click()
  await expect(page).toHaveURL(/#\/bank$/)
  await expect(page.getByRole('heading', { name: 'Question bank' })).toBeVisible()
  await expect(nav.getByRole('link', { name: 'Question bank' })).toHaveAttribute('aria-current', 'page')
  await expect(nav.getByRole('link', { name: 'Papers' })).not.toHaveAttribute('aria-current')

  // Settings lives in the avatar menu, reached by keyboard as well
  await page.getByRole('button', { name: /^Account:/ }).focus()
  await page.keyboard.press('Enter')
  await page.getByRole('menuitem', { name: 'Settings' }).click()
  await expect(page).toHaveURL(/#\/settings$/)
  await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible()
  await expect(nav.locator('[aria-current]')).toHaveCount(0)

  await nav.getByRole('link', { name: 'Papers' }).click()
  await expect(page.getByRole('heading', { name: 'Your papers' })).toBeVisible()

  // the editor has its own header, with a way back
  await newBlankPaper(page)
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
  await expect(page.getByRole('navigation', { name: 'Main' })).toHaveCount(0)
  await page.getByRole('link', { name: 'Back to papers' }).click()
  await expect(nav.getByRole('link', { name: 'Papers' })).toHaveAttribute('aria-current', 'page')
})

test('the header and the bank fit a phone without sideways scrolling', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 800 })
  for (const hash of ['#/', '#/bank', '#/settings']) {
    await page.goto(`/${hash}`)
    await expect(page.getByRole('navigation', { name: 'Main' })).toBeVisible()
    await expect(page.getByRole('button', { name: /^Account:/ })).toBeInViewport()
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
  }
})

test('import questions from a file on the bank page, then review one', async ({ page }) => {
  const base = JSON.parse(fs.readFileSync('tests/fixtures/sourced/psle_2023_ratio.json', 'utf8'))
  const stamp = Date.now().toString(36)
  const good = { ...base, id: `sourced:e2e-bank-page-${stamp}` }
  const broken = { ...base, id: `sourced:e2e-bank-broken-${stamp}`, question: { ...base.question, total_marks: undefined } }

  await page.goto('/#/bank')
  await expect(page.getByText('Your bank is empty.')).toBeVisible()
  await page.getByRole('button', { name: 'Import questions from a file' }).click()
  const dialog = page.getByRole('dialog', { name: 'Import questions from a file' })
  await dialog.getByLabel('Choose JSON files').setInputFiles([
    { name: 'good.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(good)) },
    { name: 'broken.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(broken)) },
  ])
  await dialog.getByRole('button', { name: 'Import', exact: true }).click()
  const results = dialog.getByRole('list', { name: 'Import results' })
  await expect(results.locator('[data-status="imported"]')).toHaveCount(1)
  await expect(results.locator('[data-status="invalid"]')).toHaveCount(1)

  // the same file again is a duplicate, unless Replace is ticked
  await dialog.getByLabel('Choose JSON files').setInputFiles([
    { name: 'good.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(good)) },
  ])
  await dialog.getByRole('button', { name: 'Import', exact: true }).click()
  await expect(results.locator('[data-status="duplicate"]')).toHaveCount(1)
  await dialog.getByLabel(/Replace existing questions/).check()
  await dialog.getByRole('button', { name: 'Import', exact: true }).click()
  await expect(results.locator('[data-status="replaced"]')).toHaveCount(1)
  await dialog.getByRole('button', { name: 'Back to bank' }).click()
  await expect(dialog).toHaveCount(0)

  // listed, unreviewed, and drawn by the engine
  const card = page.getByTestId('bank-question')
  await expect(card).toHaveCount(1)
  await expect(page.getByTestId('bank-count')).toHaveText('1 question')
  await expect(card.getByText('Unreviewed')).toBeVisible()
  await expect(card.getByTestId('fragment')).toBeVisible()

  // the filters narrow it; a search that matches nothing says so
  await page.getByLabel('Review').selectOption('reviewed')
  await expect(page.getByText('No questions match these filters.')).toBeVisible()
  await page.getByRole('button', { name: 'Clear filters' }).click()
  await expect(card).toHaveCount(1)

  // review is a deliberate act
  await card.getByRole('button', { name: 'Mark as reviewed…' }).click()
  await card.getByLabel(/I have checked this question/).check()
  await card.getByRole('button', { name: 'Mark as reviewed', exact: true }).click()
  await expect(card.getByText('Reviewed', { exact: true })).toBeVisible()
  const bank = await (await page.request.get(`${API}/bank`)).json()
  expect(bank.items.map((i) => [i.id, i.reviewed])).toEqual([[good.id, true]])
})
