import { test, expect } from '@playwright/test'

/**
 * Browser acceptance for P8d: on a generated paper, swap questions (another topic, write my
 * own), lock one, and "Regenerate unlocked" keeps the locked question while the sections stay
 * at their marks targets. Needs the API with EXAM_DEV_AUTH (playwright.config.js).
 */
test('swap, lock and regenerate a generated P6 Paper 2', async ({ page }) => {
  await page.goto('/')
  const form = page.getByRole('form', { name: 'Generate a paper' })
  await form.getByLabel('Paper to generate').selectOption('p2')
  await form.getByLabel('Level').selectOption('P6')
  await form.getByRole('button', { name: 'Generate paper' }).click()
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
  const id = page.url().split('/docs/')[1]
  const sectionA = page.locator('.section-block').nth(0).locator('.section-summary')
  await expect(sectionA).toHaveText('Questions 1–5 · 10 / 10 marks')

  const blocks = page.getByTestId('question-block')
  await expect(blocks).toHaveCount(19)

  // Lock question 1.
  const first = blocks.nth(0)
  await first.hover()
  await first.getByRole('button', { name: 'Lock' }).click()
  await expect(first.getByRole('button', { name: 'Locked' })).toHaveAttribute('aria-pressed', 'true')
  await expect(first.getByRole('button', { name: 'Another topic' })).toBeDisabled()
  const lockedText = await first.locator('.main').first().innerText()

  // Question 2: "Write my own" leaves a 2-mark placeholder; the section stays at 10 marks.
  const second = blocks.nth(1)
  await second.hover()
  await second.getByRole('button', { name: 'Write my own' }).click()
  await expect(page.getByTestId('placeholders-left')).toHaveText('1 placeholder to write')
  await expect(page.locator('.ff-placeholder-hint:visible')).toHaveText(/write a 2-mark short-answer question/)
  await expect(sectionA).toHaveText('Questions 1–5 · 10 / 10 marks')

  // Question 3 (now the second generated block): another topic, same marks.
  const third = blocks.nth(1)
  const before = await third.innerText()
  await third.hover()
  await third.getByRole('button', { name: 'Another topic' }).click()
  await expect(page.getByText(/Swapped in a 2-mark/)).toBeVisible()
  await expect(third).not.toHaveText(before)
  await expect(sectionA).toHaveText('Questions 1–5 · 10 / 10 marks')

  // Regenerate: the locked question stays, the placeholder is filled, targets hold.
  await page.getByRole('button', { name: 'Regenerate unlocked' }).click()
  await expect(page.getByText(/Regenerated 18 questions; kept 1/)).toBeVisible()
  await expect(page.getByTestId('placeholders-left')).toHaveCount(0)
  await expect(blocks.nth(0).locator('.main').first()).toHaveText(lockedText)
  await expect(sectionA).toHaveText('Questions 1–5 · 10 / 10 marks')
  await expect(page.locator('.section-block').nth(1).locator('.section-summary')).toHaveText(
    'Questions 6–19 · 45 / 45 marks',
  )

  // What the server stored is what the editor shows (the lock survives a reload).
  await page.reload()
  await expect(page.getByTestId('question-block').nth(0).getByRole('button', { name: 'Locked' })).toHaveCount(1)
  const stored = await (await page.request.get(`http://localhost:8000/documents/${id}`)).json()
  const locked = stored.document.content.content.filter((n) => n.attrs && n.attrs.locked === true)
  expect(locked).toHaveLength(1)
})
