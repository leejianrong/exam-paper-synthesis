import { test, expect } from '@playwright/test'
import { generateSinglePaper } from './helpers.js'

/**
 * Browser acceptance for P8a: generate a whole paper in one click from the papers list, land in
 * the ordinary editor with the generator's report, see placeholders for what couldn't be
 * filled, and check the printed paper. Needs the API with EXAM_DEV_AUTH (playwright.config.js).
 */
test('generate a P6 Paper 2: a full paper with a cover, sections at their targets, no placeholders', async ({ page }) => {
  await page.goto('/')
  await generateSinglePaper(page, 'Paper 2', 'P6')
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
  const id = page.url().split('/docs/')[1]

  await expect(page.getByTestId('generate-report')).toContainText('Filled 17 of 17 questions')
  await expect(page.getByTestId('generate-report')).toContainText('Section B has 10 multi-part questions; 2 single-part questions stand in for the rest')
  await expect(page.locator('.cover-block')).toHaveCount(1)
  await expect(page.locator('.cover-block').getByLabel('Cover level')).toHaveValue('Primary 6')
  await expect(page.locator('.section-block')).toHaveCount(2)
  await expect(page.locator('.section-block').nth(0).locator('.section-summary')).toHaveText(
    'Questions 1–5 · 10 / 10 marks',
  )
  await expect(page.locator('.section-block').nth(1).locator('.section-summary')).toHaveText(
    /Questions 6–1[78] · 45 \/ 45 marks/,
  )
  await expect(page.getByTestId('placeholders-left')).toHaveCount(0)
  await expect(page.getByLabel('Paper time in minutes')).toHaveValue('90')

  const student = await (await page.request.get(`http://localhost:8000/documents/${id}/preview/student`)).text()
  expect(student).toContain('<p class="cover-level">Primary 6</p><p class="cover-subject">Mathematics</p>')
  // Real section headers (EXA-139): Section A states its marks, structured Section B points at the [n]
  expect(student).toContain('Questions <b>1</b> to <b>5</b> carry 2 marks each.')
  expect(student).toContain('The number of marks available is shown in brackets [ ]')
  expect(student).toContain('<span class="section-total">(45 marks)</span>')

  // The banner goes away when dismissed and does not come back on reload.
  await page.getByTestId('generate-report').getByRole('button', { name: 'Dismiss' }).click()
  await expect(page.getByTestId('generate-report')).toHaveCount(0)
})

test('generate a P5 Booklet B: every slot filled, numbered on from Booklet A', async ({ page }) => {
  await page.goto('/')
  await generateSinglePaper(page, 'Paper 1 · Booklet B', 'P5')
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)

  // every 2-mark slot filled since EXA-154 (2-mark medium rungs for five more topics)
  await expect(page.getByTestId('generate-report')).toContainText('Filled 15 of 15 questions')
  await expect(page.getByTestId('placeholders-left')).toHaveCount(0)
  // Booklet B numbers on from A (EXA-134), in a 1-mark and a 2-mark section as real papers (EXA-139)
  await expect(page.locator('.section-block .section-summary')).toHaveText([
    'Questions 16–20 · 5 / 5 marks',
    'Questions 21–30 · 20 / 20 marks',
  ])
})

test('generate a P5 Paper 2: placeholders for what the content cannot fill yet', async ({ page }) => {
  await page.goto('/')
  await generateSinglePaper(page, 'Paper 2', 'P5')
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)

  // P5 has too few 3-5 mark blueprints for Section B: 16 stand-ins and 1 placeholder
  await expect(page.getByTestId('generate-report')).toContainText('Filled 21 of 22 questions')
  await expect(page.getByTestId('placeholders-left')).toHaveText('1 placeholder to write')
  const hints = page.locator('.ff-placeholder-hint:visible')
  await expect(hints).toHaveCount(1)
  await expect(hints.first()).toHaveText(/write a [345]-mark structured question here/)

  // Writing a placeholder's question clears it.
  await page.locator('.ffblock.placeholder-slot .ff-body').first().click()
  await page.keyboard.type('What is 3 + 4?')
  await expect(page.getByTestId('placeholders-left')).toHaveCount(0)
})

test('generate a P6 Booklet A: multiple-choice questions with four options each', async ({ page }) => {
  await page.goto('/')
  await generateSinglePaper(page, 'Paper 1 · Booklet A', 'P6')
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
  const id = page.url().split('/docs/')[1]

  // every slot filled since P8e batch 3 (EXA-145): ten 1-mark and five 2-mark questions
  await expect(page.getByTestId('generate-report')).toContainText('Filled 15 of 15 questions')
  await expect(page.getByTestId('generate-report')).not.toContainText('still to write')
  await expect(page.getByTestId('placeholders-left')).toHaveCount(0)

  const student = await (await page.request.get(`http://localhost:8000/documents/${id}/preview/student`)).text()
  // text options in one column, picture options (cube views, EXA-147) in a grid
  expect(student.match(/<ol class="options[ "]/g)).toHaveLength(15)
  expect(student).not.toContain('class="option option-correct"') // the right option never reaches the paper
  const key = await (await page.request.get(`http://localhost:8000/documents/${id}/preview/key`)).text()
  expect(key.match(/option option-correct/g)).toHaveLength(15)
})
