import { test, expect } from '@playwright/test'
import { settled, newFromTemplate } from './helpers.js'
import { API } from './ports.js'

/**
 * Browser acceptance for P4 paper structure: start from the Paper 2 template, see its sections
 * and paper time, add a question, watch a section's derived range / marks / target update,
 * edit a section and the time, add another section, reload, and check the student paper
 * and the PDF carry the structure. Needs the API with EXAM_DEV_AUTH (playwright.config.js).
 */
test('start from the Paper 2 template, structure the paper, reload, preview and export', async ({ page }) => {
  await page.goto('/')
  await newFromTemplate(page, 'Paper 2')
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
  const id = page.url().split('/docs/')[1]

  // The template is an ordinary paper: two sections with targets, and the paper time.
  const sections = page.locator('.section-block')
  await expect(sections).toHaveCount(2)
  await expect(sections.nth(0).getByLabel('Section title')).toHaveValue('Section A')
  await expect(sections.nth(1).getByLabel('Section title')).toHaveValue('Section B')
  await expect(sections.nth(1).getByLabel('Marks target')).toHaveValue('45')
  await expect(page.getByLabel('Paper time in minutes')).toHaveValue('90')
  await expect(sections.nth(0).locator('.section-summary')).toHaveText('No questions yet')

  // A question appended at the end lands in Section B; the summary is derived, not typed.
  await page.getByRole('button', { name: 'Add question' }).click()
  await page.getByRole('dialog', { name: 'Add question' }).getByRole('tab', { name: 'Free-form' }).click()
  const block = page.locator('.ffblock')
  await expect(block).toHaveCount(1)
  await page.keyboard.type('Ann has 12 sweets and gives away 5. How many are left?')
  await block.getByLabel('Marks').fill('3')
  await block.getByLabel('Marks').press('Enter')
  const summaryB = sections.nth(1).locator('.section-summary')
  await expect(summaryB).toHaveText('Question 1 · 3 / 45 marks')
  await expect(summaryB).toHaveAttribute('data-state', 'under')

  // Edit a section and the paper time; a target equal to the marks clears the warning.
  await sections.nth(1).getByLabel('Marks target').fill('3')
  await expect(summaryB).toHaveText('Question 1 · 3 / 3 marks')
  await expect(summaryB).toHaveAttribute('data-state', 'ok')
  await sections.nth(0).getByLabel('Section title').fill('Part One')
  await page.getByLabel('Paper time in minutes').fill('75')

  // The toolbar adds a section too.
  await page.getByRole('button', { name: 'Section', exact: true }).click()
  await expect(sections).toHaveCount(3)

  await settled(page)
  await page.reload()
  await expect(sections).toHaveCount(3)
  await expect(sections.nth(0).getByLabel('Section title')).toHaveValue('Part One')
  await expect(sections.nth(1).getByLabel('Marks target')).toHaveValue('3')
  await expect(page.getByLabel('Paper time in minutes')).toHaveValue('75')
  await expect(sections.nth(1).locator('.section-summary')).toHaveText('Question 1 · 3 / 3 marks')

  const student = await (await page.request.get(`${API}/documents/${id}/preview/student`)).text()
  // Only a teacher's own title prints; generic labels and empty titles do not (EXA-139).
  expect(student.match(/<h2 class="section-title">([^<]*)<\/h2>/g)).toEqual([
    '<h2 class="section-title">Part One</h2>',
  ])
  expect(student).toContain('The number of marks available is shown in brackets [ ]')
  expect(student).toContain('<span class="section-total">(3 marks)</span>')
  expect(student).toContain('Time: 1 h 15 min')
  const key = await (await page.request.get(`${API}/documents/${id}/preview/key`)).text()
  expect(key).not.toContain('<div class="paper-section">')

  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'Student PDF' }).click(),
  ])
  expect(download.suggestedFilename()).toMatch(/\.pdf$/)
})

test('the marking margin follows the section mode and can be switched per section', async ({ page }) => {
  await page.goto('/')
  await newFromTemplate(page, 'Paper 1 · Booklet B')
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
  const id = page.url().split('/docs/')[1]

  // Booklet B is short-answer: the margin is on by default, and the student paper prints it.
  // A question added at the end lands in its last (2-mark) section.
  const section = page.locator('.section-block').last()
  await expect(section.getByLabel('Marking margin')).toBeChecked()
  await page.getByRole('button', { name: 'Add question' }).click()
  await page.getByRole('dialog', { name: 'Add question' }).getByRole('tab', { name: 'Free-form' }).click()
  await page.keyboard.type('Ann has 12 sweets and gives away 5. How many are left?')
  await page.locator('.ffblock').getByLabel('Marks').fill('2')
  await page.locator('.ffblock').getByLabel('Marks').press('Enter')
  await settled(page)
  const preview = async () =>
    (await (await page.request.get(`${API}/documents/${id}/preview/student`)).text()).split('</style>').pop()
  expect(await preview()).toMatch(/<section data-marks="2" class="question marked freeform"/)
  expect(await preview()).toMatch(/<main [^>]*data-tally/) // the paginator gives each page a tally box
  // A short-answer section prints no [n]: the header gives the marks (EXA-139). Opt in per section.
  expect(await preview()).not.toContain('<span class="marks">[2]</span>')
  // The editing page shows the question as it prints (EXA-152): no [2] in this section yet.
  const ff = page.locator('.ffblock')
  await expect(ff.locator('.ff-area .marks')).toHaveCount(0)
  await section.getByLabel('Marks shown').selectOption('answer')
  await expect(ff.locator('.ff-area .marks')).toHaveText('[2]')
  await settled(page)
  expect(await preview()).toMatch(/<span class="ans-blank"><\/span><span class="marks">\[2\]<\/span>/)

  // The editor's Preview reads what the paginator decided: pages, their questions and tallies.
  await page.getByRole('button', { name: 'Preview' }).click()
  const pages = page.getByLabel('Pages', { exact: true })
  // The template's cover page is a page of its own, then the blank back of the cover, before
  // the questions; the booklet is padded to an even page count (EXA-140).
  await expect(pages).toContainText('4 pages')
  await expect(pages).toContainText('cover page')
  await expect(pages).toContainText('blank page')
  await expect(pages).toContainText('Q16 · 2 marks') // Booklet B numbers on from A (EXA-134)
  await page.getByRole('button', { name: 'Close preview' }).click()

  // Booklet B's first section is short-answer too (EXA-139): switch its margin off as well,
  // so only the section under test decides whether a tally prints.
  await page.locator('.section-block').first().getByLabel('Marking margin').uncheck()
  // Switch it off: no margin. Change the mode to multiple choice: still off. Choose it on: margin.
  await section.getByLabel('Marking margin').uncheck()
  await settled(page)
  expect(await preview()).not.toContain('question marked')
  expect(await preview()).not.toMatch(/<main [^>]*data-tally/)
  await section.getByLabel('Mode').selectOption('mcq')
  await expect(section.getByLabel('Marking margin')).not.toBeChecked()
  await section.getByLabel('Marking margin').check()
  await settled(page)
  expect(await preview()).toContain('question marked')

  await page.reload()
  await expect(page.locator('.section-block').last().getByLabel('Marking margin')).toBeChecked()
  await expect(page.locator('.section-block').last().getByLabel('Marks shown')).toHaveValue('answer')
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'Student PDF' }).click(),
  ])
  expect(download.suggestedFilename()).toMatch(/\.pdf$/)
})
