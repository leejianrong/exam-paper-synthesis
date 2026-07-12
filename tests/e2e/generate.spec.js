import { test, expect } from '@playwright/test'

/**
 * Browser acceptance test for the real Generate flow.
 *
 * Drives the Svelte SPA in a headless browser: clicking Generate calls the live
 * FastAPI engine (POST /generate → ratio_medium), and a QuestionCard is
 * prepended. We assert the acceptance surface that was previously only checked
 * at the API level: the validation badge, question text, answer, bar-model SVG,
 * and the expandable M/A/B answer key.
 */
test('Generate produces a validated ratio question card', async ({ page }) => {
  await page.goto('/')

  // The Generate button is the single call-to-action on the landing page.
  const generate = page.getByRole('button', { name: 'Generate' })
  await expect(generate).toBeVisible()
  await generate.click()

  // Auto-wait for the first card to render (the API round-trip drives this).
  const card = page.locator('article.card').first()
  await expect(card).toBeVisible()

  // Validation badge must read "pass".
  const badge = card.locator('.badge.pass')
  await expect(badge).toBeVisible()
  await expect(badge).toHaveText('pass')

  // Question text is present and non-empty.
  const questionText = await card.locator('p.text').innerText()
  expect(questionText.trim().length).toBeGreaterThan(0)

  // Answer line shows a value beyond the "Answer" label.
  const answer = card.locator('p.answer')
  await expect(answer).toBeVisible()
  const answerText = (await answer.innerText()).replace(/answer/i, '').trim()
  expect(answerText.length).toBeGreaterThan(0)

  // Bar-model SVG is rendered inside the card.
  const svg = card.locator('[aria-label="bar model"] svg')
  await expect(svg).toBeVisible()

  // Worked solution section is present.
  await expect(card.getByRole('heading', { name: /Worked solution/i })).toBeVisible()

  // The detailed answer key is collapsed until the toggle is clicked.
  const toggle = card.getByRole('button', { name: /detailed answer key \(M\/A\/B\)/i })
  await expect(toggle).toBeVisible()
  await expect(card.locator('ul.scheme')).toHaveCount(0)

  await toggle.click()

  // Expanding reveals M/A/B marking rows.
  const scheme = card.locator('ul.scheme')
  await expect(scheme).toBeVisible()
  await expect(scheme.locator('li')).not.toHaveCount(0)
  // At least one row carries an M/A/B tag.
  await expect(scheme.locator('.mtag').first()).toBeVisible()
})
