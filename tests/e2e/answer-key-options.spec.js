import { test, expect } from '@playwright/test'
import { settled, newBlankPaper, editAnswer, exportPdf, showKey, showPaper } from './helpers.js'
import { API } from './ports.js'

/**
 * Browser acceptance for the answer key view (EXA-162) and its options. The header's Paper |
 * Answer key switch shows the key exactly as it prints (the server's own key HTML), with the
 * options in a strip above it. A new paper has the school key (EXA-159): the answers and short
 * working only, no marks, no M1/A1. Marks come back with a tick; worked solutions are the other
 * style. A question leaves the key from its ⋯ menu; the key view names it and puts it back.
 * Reload keeps everything, and the printed key keeps the paper's numbering while the student
 * paper is untouched.
 */
async function addFreeform(page, text, marks) {
  await page.getByRole('button', { name: 'Add question' }).click()
  await page.getByRole('dialog', { name: 'Add question' }).getByRole('tab', { name: 'Write my own' }).click()
  await page.keyboard.type(text)
  // a fixed index: .last() would follow the next question added
  const block = page.locator('.ffblock').nth((await page.locator('.ffblock').count()) - 1)
  await block.getByLabel('Marks').fill(String(marks))
  await block.getByLabel('Marks').press('Enter')
  return block
}

async function writeAnswer(page, block, answer) {
  await block.locator('.ff-body p').first().click()
  const dialog = await editAnswer(page, block)
  await page.keyboard.type(answer)
  await dialog.getByRole('button', { name: 'Done' }).click()
}

const printedKey = async (page, id) =>
  (await (await page.request.get(`${API}/documents/${id}/preview/key`)).text()).split('</style>').pop()

test('the answer key view: school key by default, its options, leaving a question out', async ({ page }) => {
  await page.goto('/')
  await newBlankPaper(page)
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
  const id = page.url().split('/docs/')[1]

  const one = await addFreeform(page, 'QONE-TEXT how many sweets?', 2)
  await writeAnswer(page, one, 'ANSWER-ONE')
  const two = await addFreeform(page, 'QTWO-TEXT how many apples?', 3)
  await writeAnswer(page, two, 'ANSWER-TWO')

  // The key view: the school key by default, no question text, no marks, no M1/A1.
  const key = await showKey(page)
  await expect(page.locator('.surface')).toBeHidden()
  const view = page.getByRole('region', { name: 'Answer key' })
  const strip = view.getByRole('group', { name: 'Answer key options' })
  await expect(strip.getByRole('radio', { name: 'School key' })).toBeChecked()
  await expect(strip.getByRole('checkbox', { name: 'Marking scheme (M1, A1)' })).not.toBeChecked()
  await expect(strip.getByRole('checkbox', { name: 'The question' })).toHaveCount(0)
  await expect(key.locator('.compact-key')).toBeVisible()
  await expect(key.locator('body')).toContainText('ANSWER-TWO')
  await expect(key.locator('body')).not.toContainText('QTWO-TEXT')
  await expect(key.locator('.key-marks')).toHaveCount(0)

  // Marks are one tick away, and the view redraws to show them.
  await strip.getByRole('checkbox', { name: 'Marks' }).check()
  await expect(key.locator('.key-marks').filter({ hasText: '[3]' })).toBeVisible()

  // Question 1 comes out of the key from its ⋯ menu; the key view names it, and redraws without it.
  await showPaper(page)
  await one.locator('.ff-body p').first().click()
  await one.getByRole('button', { name: /^More actions/ }).click()
  await one.getByRole('menuitem', { name: 'Leave out of answer key', exact: true }).click()
  await showKey(page)
  await expect(view.getByRole('button', { name: 'Include question 1 in the answer key' })).toBeVisible()
  await expect(key.locator('body')).not.toContainText('ANSWER-ONE')
  await expect(key.locator('th[scope=row]')).toHaveText(['Q2']) // numbered 2, not 1

  // Worked solutions repeat the question; hide it and the key drops it too.
  await strip.getByRole('radio', { name: 'Worked solutions' }).check()
  await expect(key.locator('body')).toContainText('QTWO-TEXT')
  await strip.getByRole('checkbox', { name: 'The question' }).uncheck()
  await expect(key.locator('body')).not.toContainText('QTWO-TEXT')

  await settled(page)
  await page.reload()
  await showKey(page)
  await expect(strip.getByRole('radio', { name: 'Worked solutions' })).toBeChecked()
  await expect(strip.getByRole('checkbox', { name: 'The question' })).not.toBeChecked()
  // switching to worked solutions brought back their M1/A1 lines
  await expect(strip.getByRole('checkbox', { name: 'Marking scheme (M1, A1)' })).toBeChecked()
  await expect(view.getByRole('button', { name: 'Include question 1 in the answer key' })).toBeVisible()

  let printed = await printedKey(page, id)
  expect(printed).toContain('ANSWER-TWO')
  expect(printed).not.toContain('ANSWER-ONE')
  expect(printed).not.toContain('QTWO-TEXT')
  expect(printed.match(/counter-reset: q (\d+)/g)).toEqual(['counter-reset: q 1']) // numbered 2, not 1
  const student = await (await page.request.get(`${API}/documents/${id}/preview/student`)).text()
  expect(student).toContain('QONE-TEXT')
  expect(student).toContain('QTWO-TEXT')

  // Putting everything back restores the full worked solutions.
  await strip.getByRole('checkbox', { name: 'The question' }).check()
  await view.getByRole('button', { name: 'Include question 1 in the answer key' }).click()
  await expect(view.getByRole('button', { name: /Include question 1/ })).toHaveCount(0)
  await expect(key.locator('body')).toContainText('ANSWER-ONE')
  await expect(key.locator('body')).toContainText('QONE-TEXT')
  await settled(page)
  printed = await printedKey(page, id)
  expect(printed).toContain('ANSWER-ONE')
  expect(printed).toContain('QONE-TEXT')

  // Ctrl+Alt+K goes back to the paper.
  await page.keyboard.press('Control+Alt+k')
  await expect(page.locator('.surface')).toBeVisible()

  const [download] = await Promise.all([
    page.waitForEvent('download'),
    exportPdf(page, 'Answer key (PDF)'),
  ])
  expect(download.suggestedFilename()).toMatch(/\.pdf$/)
})
