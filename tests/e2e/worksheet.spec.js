import { test, expect } from '@playwright/test'

/**
 * Browser acceptance test for the V4 review gate + worksheet tray.
 *
 * Drives the Svelte SPA in a headless browser against the live FastAPI engine:
 * generate two cards, Approve one (it appears in the WorksheetTray with the
 * correct running total marks and the card flips to its "Added" state), then
 * Discard the other (it is removed from the review list only). Mirrors the
 * harness of generate.spec.js.
 */
test('Approve adds to the worksheet tray; Discard removes a review card', async ({ page }) => {
  await page.goto('/')

  // Generate two cards (each click prepends one) so we can approve one and
  // discard a different one.
  const generate = page.getByRole('button', { name: 'Generate', exact: true })
  await expect(generate).toBeVisible()
  await generate.click()
  await expect(page.locator('article.card')).toHaveCount(1)
  await generate.click()
  await expect(page.locator('article.card')).toHaveCount(2)

  // The tray starts empty.
  const tray = page.locator('aside.tray')
  await expect(tray).toBeVisible()
  await expect(tray.locator('.empty')).toBeVisible()

  // Approve the first card.
  const approvedCard = page.locator('article.card').first()
  const approvedText = (await approvedCard.locator('p.text').innerText()).trim()
  await approvedCard.getByRole('button', { name: 'Approve' }).click()

  // The card flips to its "Added" state and Approve is gone.
  await expect(approvedCard.locator('.added')).toHaveText('✓ Added to worksheet')
  await expect(approvedCard.getByRole('button', { name: 'Approve' })).toHaveCount(0)

  // One item now sits in the tray with the correct running total marks.
  const items = tray.locator('ol.items > li.item')
  await expect(items).toHaveCount(1)
  const itemMarks = (await items.first().locator('.marks').innerText()).trim()
  const totalMarks = (await tray.locator('p.total b').innerText()).trim()
  expect(totalMarks).toBe(itemMarks)
  // Running total is a real, non-empty [N] value.
  expect(totalMarks).toMatch(/^\[\d+\]$/)

  // Discard a DIFFERENT card — it leaves the review list only.
  const discardedCard = page.locator('article.card').nth(1)
  const discardedText = (await discardedCard.locator('p.text').innerText()).trim()
  await discardedCard.getByRole('button', { name: 'Discard' }).click()

  // The review list drops to one card; the discarded question is gone.
  await expect(page.locator('article.card')).toHaveCount(1)
  await expect(page.locator('article.card p.text')).not.toHaveText(discardedText)

  // The approved card remains, still in its "Added" state, and the tray keeps it.
  await expect(page.locator('article.card p.text').first()).toHaveText(approvedText)
  await expect(page.locator('article.card').first().locator('.added')).toBeVisible()
  await expect(items).toHaveCount(1)
})
