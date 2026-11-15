import { test, expect } from '@playwright/test'
import { settled } from './helpers.js'

/**
 * Browser acceptance for P7: add a cover page and a blank page from the toolbar, fill the cover,
 * reload, and check the student paper prints the cover in place of the header while the answer
 * key leaves both out. Needs the API with EXAM_DEV_AUTH (playwright.config.js).
 */
test('add a cover page and a blank page, reload, and preview them', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Paper 2', exact: true }).click()
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
  const id = page.url().split('/docs/')[1]

  // The cover goes first, and only once: the button is disabled after.
  const coverButton = page.getByRole('button', { name: 'Cover page', exact: true })
  await coverButton.click()
  const cover = page.locator('.cover-block')
  await expect(cover).toHaveCount(1)
  await expect(coverButton).toBeDisabled()
  await expect(page.locator('.surface .ProseMirror > *').first()).toHaveClass(/cover-block/)
  await cover.getByLabel('Cover school').fill('Pandan Primary School')
  await cover.getByLabel('Cover level').fill('Primary 6')
  await cover.getByLabel('Cover paper').fill('Paper 2')
  await cover.getByLabel('Cover instructions').fill('Answer all questions.\nShow your working.')

  // A blank page lands where the cursor is; make it rough work.
  await page.locator('.surface .ProseMirror').click()
  await page.getByRole('button', { name: 'Blank page', exact: true }).click()
  const blank = page.locator('.blank-block')
  await expect(blank).toHaveCount(1)
  await blank.getByLabel('Blank page kind').selectOption('rough')

  await settled(page)
  await page.reload()
  await expect(cover).toHaveCount(1)
  await expect(cover.getByLabel('Cover school')).toHaveValue('Pandan Primary School')
  await expect(blank.getByLabel('Blank page kind')).toHaveValue('rough')

  const student = await (await page.request.get(`http://localhost:8000/documents/${id}/preview/student`)).text()
  expect(student).toContain('<p class="cover-school">Pandan Primary School</p>')
  expect(student).toContain('<p class="cover-subject">Primary 6 Mathematics</p>')
  expect(student).toContain('<li>Answer all questions.</li><li>Show your working.</li>')
  expect(student).toContain('Time: 1 h 30 min')
  expect(student).not.toContain('<header class="sheet-header">')
  expect(student).toContain('<div class="blank-page rough"><p class="blank-text">Rough work</p>')
  const key = await (await page.request.get(`http://localhost:8000/documents/${id}/preview/key`)).text()
  expect(key).not.toContain('<div class="cover-page">')
  expect(key).not.toContain('<div class="blank-page')
})
