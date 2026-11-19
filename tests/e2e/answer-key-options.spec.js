import { test, expect } from '@playwright/test'
import { settled, newBlankPaper, paperTab, exportPdf } from './helpers.js'
import { API } from './ports.js'

/**
 * Browser acceptance for the answer-key options. A new paper has the school key (EXA-159): the
 * answers and short working only, no marks, no M1/A1. Marks come back with a tick; worked
 * solutions are the other style. Then the P5 options: leave a question out, hide the question
 * text, see the editor's key view follow, reload, and check the printed key keeps the paper's
 * numbering while the student paper is untouched.
 */
async function addFreeform(page, text, marks) {
  await page.getByRole('button', { name: 'Add question' }).click()
  await page.getByRole('dialog', { name: 'Add question' }).getByRole('tab', { name: 'Write my own' }).click()
  await page.keyboard.type(text)
  const block = page.locator('.ffblock').last()
  await block.getByLabel('Marks').fill(String(marks))
  await block.getByLabel('Marks').press('Enter')
}

const printedKey = async (page, id) =>
  (await (await page.request.get(`${API}/documents/${id}/preview/key`)).text()).split('</style>').pop()

test('a new paper has the school key; marks, worked solutions and leaving questions out are options', async ({ page }) => {
  await page.goto('/')
  await newBlankPaper(page)
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
  const id = page.url().split('/docs/')[1]

  await addFreeform(page, 'QONE-TEXT how many sweets?', 2)
  await addFreeform(page, 'QTWO-TEXT how many apples?', 3)

  const key = page.getByRole('region', { name: 'Answer key' })
  const entries = key.locator('li.entry')
  await expect(entries).toHaveCount(2)
  await entries.nth(0).locator('.answer').click()
  await page.keyboard.type('ANSWER-ONE')
  await entries.nth(1).locator('.answer').click()
  await page.keyboard.type('ANSWER-TWO')

  // The school key by default: no question text, no marks, no M1/A1. (The key options sit on
  // the side panel's Paper tab for now, EXA-160.)
  await paperTab(page)
  const style = page.getByLabel('Answer key style')
  await expect(style).toHaveValue('compact')
  await expect(style.locator('option:checked')).toHaveText('School key')
  await expect(page.getByLabel('Answer key shows the marking scheme (M1, A1)')).not.toBeChecked()
  await expect(page.getByLabel('Answer key repeats each question')).toHaveCount(0)
  await settled(page)
  let printed = await printedKey(page, id)
  expect(printed).toContain('class="compact-key"')
  expect(printed).toContain('<span class="ans-label">Ans:</span> ANSWER-TWO')
  expect(printed).not.toContain('QTWO-TEXT')
  expect(printed).not.toContain('key-marks')

  // Marks are one tick away.
  await page.getByLabel("Answer key shows each question's marks").check()
  await settled(page)
  printed = await printedKey(page, id)
  expect(printed).toContain('<span class="key-marks">[3]</span>')

  // Question 1 comes out of the key; the editor's view dims it but keeps its number.
  await key.getByLabel('Include question 1 in the answer key').uncheck()
  await expect(entries.nth(0)).toHaveClass(/excluded/)
  await expect(entries.nth(0)).toContainText('1.')

  // Worked solutions repeat the question; hide it and the key view drops it too.
  await style.selectOption('full')
  await expect(entries.nth(1)).toContainText('QTWO-TEXT')
  await page.getByLabel('Answer key repeats each question').uncheck()
  await expect(entries.nth(1)).not.toContainText('QTWO-TEXT')

  await settled(page)
  await page.reload()
  await expect(page.getByLabel('Answer key style')).toHaveValue('full')
  await expect(page.getByLabel('Answer key repeats each question')).not.toBeChecked()
  // switching to worked solutions brought back their M1/A1 lines
  await expect(page.getByLabel('Answer key shows the marking scheme (M1, A1)')).toBeChecked()
  await expect(key.getByLabel('Include question 1 in the answer key')).not.toBeChecked()
  await expect(key.getByLabel('Include question 2 in the answer key')).toBeChecked()

  printed = await printedKey(page, id)
  expect(printed).toContain('ANSWER-TWO')
  expect(printed).not.toContain('ANSWER-ONE')
  expect(printed).not.toContain('QTWO-TEXT')
  expect(printed.match(/counter-reset: q (\d+)/g)).toEqual(['counter-reset: q 1']) // numbered 2, not 1
  const student = await (await page.request.get(`${API}/documents/${id}/preview/student`)).text()
  expect(student).toContain('QONE-TEXT')
  expect(student).toContain('QTWO-TEXT')

  // Putting everything back restores the full worked solutions.
  await page.getByLabel('Answer key repeats each question').check()
  await key.getByLabel('Include question 1 in the answer key').check()
  await settled(page)
  const full = await printedKey(page, id)
  expect(full).toContain('ANSWER-ONE')
  expect(full).toContain('QONE-TEXT')

  const [download] = await Promise.all([
    page.waitForEvent('download'),
    exportPdf(page, 'Answer key (PDF)'),
  ])
  expect(download.suggestedFilename()).toMatch(/\.pdf$/)
})
