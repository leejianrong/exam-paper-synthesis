import { test, expect } from '@playwright/test'
import { settled, newBlankPaper, newFromTemplate } from './helpers.js'

/**
 * Browser acceptance for P7: add a cover page and a blank page from the toolbar, fill the cover,
 * reload, and check the student paper prints the cover in place of the header while the answer
 * key leaves both out. Needs the API with EXAM_DEV_AUTH (playwright.config.js).
 */
test('the toolbar adds a cover page to a new paper, first and only once', async ({ page }) => {
  await page.goto('/')
  await newBlankPaper(page)
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
  const coverButton = page.getByRole('button', { name: 'Cover page', exact: true })
  await expect(coverButton).toBeEnabled()
  await coverButton.click()
  await expect(page.locator('.cover-block')).toHaveCount(1)
  await expect(coverButton).toBeDisabled()
  await expect(page.locator('.surface .ProseMirror > *').first()).toHaveClass(/cover-block/)
})

test('a starter template comes with its cover; fill it, add a blank page, reload, preview', async ({ page }) => {
  await page.goto('/')
  await newFromTemplate(page, 'Paper 2')
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
  const id = page.url().split('/docs/')[1]

  // The template's cover is prefilled like a generated paper's; the level is the teacher's.
  const coverButton = page.getByRole('button', { name: 'Cover page', exact: true })
  const cover = page.locator('.cover-block')
  await expect(cover).toHaveCount(1)
  await expect(coverButton).toBeDisabled()
  await expect(page.locator('.surface .ProseMirror > *').first()).toHaveClass(/cover-block/)
  await expect(cover.getByLabel('Cover paper')).toHaveValue('Paper 2')
  await expect(cover.getByLabel('Cover level')).toHaveValue('')
  await expect(cover.getByLabel('Cover instructions')).toHaveValue(/approved calculator is expected/)
  await cover.getByLabel('Cover school').fill('Pandan Primary School')
  await cover.getByLabel('Cover level').fill('Primary 6')
  await cover.getByLabel('Cover instructions').fill('Answer all questions.\nShow your working.')

  // The template has a blank back of the cover (EXA-140). A blank page lands where the cursor
  // is; make one of the two rough work.
  const blank = page.locator('.blank-block')
  await expect(blank).toHaveCount(1)
  await page.locator('.surface .ProseMirror').click()
  await page.getByRole('button', { name: 'Blank page', exact: true }).click()
  await expect(blank).toHaveCount(2)
  await blank.nth(1).getByLabel('Blank page kind').selectOption('rough')

  await settled(page)
  await page.reload()
  await expect(cover).toHaveCount(1)
  await expect(cover.getByLabel('Cover school')).toHaveValue('Pandan Primary School')
  await expect(blank).toHaveCount(2)
  await expect(page.locator('.blank-block[data-kind="rough"]')).toHaveCount(1)

  const student = await (await page.request.get(`http://localhost:8000/documents/${id}/preview/student`)).text()
  expect(student).toContain('<p class="cover-school">Pandan Primary School</p>')
  expect(student).toContain('<p class="cover-level">Primary 6</p><p class="cover-subject">Mathematics</p>')
  expect(student).toContain('<li>Answer all questions.</li><li>Show your working.</li>')
  expect(student).toContain('Time: 1 h 30 min')
  expect(student).not.toContain('<header class="sheet-header">')
  expect(student).toContain('<div class="blank-page rough"><p class="blank-text">Rough work</p>')
  const key = await (await page.request.get(`http://localhost:8000/documents/${id}/preview/key`)).text()
  expect(key).not.toContain('<div class="cover-page">')
  expect(key).not.toContain('<div class="blank-page')
})

test('a selected cover is never replaced by a toolbar insert or typing (EXA-129)', async ({ page }) => {
  await page.goto('/')
  await newFromTemplate(page, 'Paper 2')
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
  const cover = page.locator('.cover-block')
  await cover.locator('.page-block-title').click() // one click selects the whole cover block
  for (const tool of ['Section', 'Blank page', 'Page break']) {
    await page.getByRole('button', { name: tool, exact: true }).click()
    await expect(cover).toHaveCount(1)
    await expect(page.locator('.surface .ProseMirror > *').first()).toHaveClass(/cover-block/)
    await cover.locator('.page-block-title').click()
  }
  await page.keyboard.type('Typed after selecting the cover')
  await expect(cover).toHaveCount(1)
  await expect(page.locator('.surface .ProseMirror > *').first()).toHaveClass(/cover-block/)
  await expect(page.locator('.surface .ProseMirror > p').first()).toContainText('Typed after selecting the cover')
})
