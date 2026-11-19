import { test, expect } from '@playwright/test'
import { settled, newBlankPaper, newFromTemplate, insertMenu, headerMenu, blockSettings } from './helpers.js'
import { API } from './ports.js'

/**
 * Browser acceptance for P7: add a cover page and a blank page from the Insert menu, fill the cover,
 * reload, and check the student paper prints the cover in place of the header while the answer
 * key leaves both out. Needs the API with EXAM_DEV_AUTH (playwright.config.js).
 */
test('the Insert menu adds a cover page to a new paper, first and only once', async ({ page }) => {
  await page.goto('/')
  await newBlankPaper(page)
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
  let menu = await insertMenu(page)
  const coverItem = menu.getByRole('menuitem', { name: 'Cover page', exact: true })
  await expect(coverItem).not.toHaveAttribute('aria-disabled')
  await coverItem.click()
  await expect(page.locator('.cover-block')).toHaveCount(1)
  menu = await insertMenu(page)
  await expect(menu.getByRole('menuitem', { name: 'Cover page', exact: true })).toHaveAttribute('aria-disabled', 'true')
  await page.keyboard.press('Escape')
  await expect(page.locator('.surface .ProseMirror > *').first()).toHaveClass(/cover-block/)
})

test('a starter template comes with its cover; fill it, add a blank page, reload, preview', async ({ page }) => {
  await page.goto('/')
  await newFromTemplate(page, 'Paper 2')
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
  const id = page.url().split('/docs/')[1]

  // The template's cover is prefilled like a generated paper's; the level is the teacher's.
  const cover = page.locator('.cover-block')
  await expect(cover).toHaveCount(1)
  const menu = await insertMenu(page)
  await expect(menu.getByRole('menuitem', { name: 'Cover page', exact: true })).toHaveAttribute('aria-disabled', 'true')
  await page.keyboard.press('Escape')
  await expect(page.locator('.surface .ProseMirror > *').first()).toHaveClass(/cover-block/)
  // On the page the cover is a compact card; its fields edit in the side panel (EXA-164).
  await expect(cover.locator('input, select, textarea')).toHaveCount(0)
  await expect(cover.locator('.cover-line').last()).toHaveText('Mathematics · Paper 2')
  let panel = await blockSettings(page, cover)
  await expect(page.getByRole('tab', { name: 'Cover page' })).toHaveAttribute('aria-selected', 'true')
  await expect(panel.getByLabel('Paper', { exact: true })).toHaveValue('Paper 2')
  await expect(panel.getByLabel('Level')).toHaveValue('')
  await expect(panel.getByLabel('Instructions')).toHaveValue(/approved calculator is expected/)
  await panel.getByLabel('School').fill('Example Primary School')
  await panel.getByLabel('Level').fill('Primary 6')
  await panel.getByLabel('Instructions').fill('Answer all questions.\nShow your working.')
  await expect(cover.locator('.cover-line').first()).toHaveText('Example Primary School')
  await expect(cover.locator('.cover-line').last()).toHaveText('Primary 6 · Mathematics · Paper 2')

  // The template has a blank back of the cover (EXA-140). A blank page lands where the cursor
  // is; make one of the two rough work.
  const blank = page.locator('.blank-block')
  await expect(blank).toHaveCount(1)
  await page.locator('.surface .ProseMirror').click()
  await (await insertMenu(page)).getByRole('menuitem', { name: 'Blank or rough-work page', exact: true }).click()
  await expect(blank).toHaveCount(2)
  await blank.nth(1).getByLabel('Blank page kind').selectOption('rough')

  await settled(page)
  await page.reload()
  await expect(cover).toHaveCount(1)
  await expect(cover.locator('.cover-line').first()).toHaveText('Example Primary School')
  // Paper > Cover page… lands on the cover's first field, in the panel
  await (await headerMenu(page, 'Paper')).getByRole('menuitem', { name: 'Cover page…' }).click()
  panel = page.locator('#tabpanel-selection')
  await expect(panel.getByLabel('School')).toBeFocused()
  await expect(panel.getByLabel('School')).toHaveValue('Example Primary School')
  await expect(blank).toHaveCount(2)
  await expect(page.locator('.blank-block[data-kind="rough"]')).toHaveCount(1)

  const student = await (await page.request.get(`${API}/documents/${id}/preview/student`)).text()
  expect(student).toContain('<p class="cover-school">Example Primary School</p>')
  expect(student).toContain('<p class="cover-level">Primary 6</p><p class="cover-subject">Mathematics</p>')
  expect(student).toContain('<li>Answer all questions.</li><li>Show your working.</li>')
  expect(student).toContain('Time: 1 h 30 min')
  expect(student).not.toContain('<header class="sheet-header">')
  expect(student).toContain('<div class="blank-page rough"><p class="blank-text">Rough work</p>')
  const key = await (await page.request.get(`${API}/documents/${id}/preview/key`)).text()
  expect(key).not.toContain('<div class="cover-page">')
  expect(key).not.toContain('<div class="blank-page')
})

test('a selected cover is never replaced by an insert or typing (EXA-129)', async ({ page }) => {
  await page.goto('/')
  await newFromTemplate(page, 'Paper 2')
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
  const cover = page.locator('.cover-block')
  await cover.locator('.cover-caption').click() // one click selects the whole cover block
  for (const tool of ['Section', 'Blank or rough-work page', 'Page break']) {
    if (tool === 'Section') await page.getByRole('button', { name: tool, exact: true }).click()
    else await (await insertMenu(page)).getByRole('menuitem', { name: tool, exact: true }).click()
    await expect(cover).toHaveCount(1)
    await expect(page.locator('.surface .ProseMirror > *').first()).toHaveClass(/cover-block/)
    await cover.locator('.cover-caption').click()
  }

  await page.keyboard.type('Typed after selecting the cover')
  await expect(cover).toHaveCount(1)
  await expect(page.locator('.surface .ProseMirror > *').first()).toHaveClass(/cover-block/)
  await expect(page.locator('.surface .ProseMirror > p').first()).toContainText('Typed after selecting the cover')
})
