import { test, expect } from '@playwright/test'

/**
 * Browser acceptance for P8a: generate a whole paper in one click from the papers list, land in
 * the ordinary editor with the generator's report, see placeholders for what couldn't be
 * filled, and check the printed paper. Needs the API with EXAM_DEV_AUTH (playwright.config.js).
 */
test('generate a P6 Paper 2: a full paper with a cover, sections at their targets, no placeholders', async ({ page }) => {
  await page.goto('/')
  const form = page.getByRole('form', { name: 'Generate a paper' })
  await expect(form.getByLabel('Paper to generate')).toHaveValue('p2')
  await form.getByLabel('Level').selectOption('P6')
  await form.getByRole('button', { name: 'Generate paper' }).click()
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
  const id = page.url().split('/docs/')[1]

  await expect(page.getByTestId('generate-report')).toContainText('Filled 17 of 17 questions')
  await expect(page.getByTestId('generate-report')).toContainText('Section B has 3 multi-part questions; 9 single-part questions stand in for the rest')
  await expect(page.locator('.cover-block')).toHaveCount(1)
  await expect(page.locator('.cover-block').getByLabel('Cover level')).toHaveValue('Primary 6')
  await expect(page.locator('.section-block')).toHaveCount(2)
  await expect(page.locator('.section-block').nth(0).locator('.section-summary')).toHaveText(
    'Questions 1–5 · 10 / 10 marks',
  )
  await expect(page.locator('.section-block').nth(1).locator('.section-summary')).toHaveText(
    'Questions 6–17 · 45 / 45 marks',
  )
  await expect(page.getByTestId('placeholders-left')).toHaveCount(0)
  await expect(page.getByLabel('Paper time in minutes')).toHaveValue('90')

  const student = await (await page.request.get(`http://localhost:8000/documents/${id}/preview/student`)).text()
  expect(student).toContain('<p class="cover-subject">Primary 6 Mathematics</p>')
  expect(student).toContain('Questions 6–17 · 45 marks · Structured')

  // The banner goes away when dismissed and does not come back on reload.
  await page.getByTestId('generate-report').getByRole('button', { name: 'Dismiss' }).click()
  await expect(page.getByTestId('generate-report')).toHaveCount(0)
})

test('generate a P5 Booklet B: placeholders for what the content cannot fill yet', async ({ page }) => {
  await page.goto('/')
  const form = page.getByRole('form', { name: 'Generate a paper' })
  await form.getByLabel('Paper to generate').selectOption('p1_booklet_b')
  await form.getByLabel('Level').selectOption('P5')
  await form.getByRole('button', { name: 'Generate paper' }).click()
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)

  await expect(page.getByTestId('generate-report')).toContainText('Filled 13 of 15 questions')
  await expect(page.getByTestId('placeholders-left')).toHaveText('2 placeholders to write')
  const hints = page.locator('.ff-placeholder-hint:visible')
  await expect(hints).toHaveCount(2)
  await expect(hints.first()).toHaveText(/write a [12]-mark short-answer question here/)
  await expect(page.locator('.section-block .section-summary')).toHaveText('Questions 16–30 · 25 / 25 marks') // Booklet B numbers on from A (EXA-134)

  // Writing a placeholder's question clears it.
  await page.locator('.ffblock.placeholder-slot .ff-body').first().click()
  await page.keyboard.type('What is 3 + 4?')
  await expect(page.getByTestId('placeholders-left')).toHaveText('1 placeholder to write')
})

test('generate a P6 Booklet A: multiple-choice questions with four options each', async ({ page }) => {
  await page.goto('/')
  const form = page.getByRole('form', { name: 'Generate a paper' })
  await form.getByLabel('Paper to generate').selectOption('p1_booklet_a')
  await form.getByLabel('Level').selectOption('P6')
  await form.getByRole('button', { name: 'Generate paper' }).click()
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
  const id = page.url().split('/docs/')[1]

  await expect(page.getByTestId('generate-report')).toContainText('Filled 13 of 15 questions')
  await expect(page.getByTestId('generate-report')).toContainText('2 multiple-choice questions still to write')
  await expect(page.getByTestId('placeholders-left')).toHaveText('2 placeholders to write')

  const student = await (await page.request.get(`http://localhost:8000/documents/${id}/preview/student`)).text()
  expect(student.match(/<ol class="options">/g)).toHaveLength(13)
  expect(student).not.toContain('class="option option-correct"') // the right option never reaches the paper
  const key = await (await page.request.get(`http://localhost:8000/documents/${id}/preview/key`)).text()
  expect(key.match(/option option-correct/g)).toHaveLength(13)
})
