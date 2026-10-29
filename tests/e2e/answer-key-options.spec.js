import { test, expect } from '@playwright/test'

/**
 * Browser acceptance for P5 answer-key options: leave a question out of the key, hide the
 * question text and the M/A breakdown, see the editor's key view follow, reload, and check the
 * printed key keeps the paper's numbering while the student paper is untouched.
 */
async function addFreeform(page, text, marks) {
  await page.getByRole('button', { name: 'Add question' }).click()
  await page.getByRole('dialog', { name: 'Add question' }).getByRole('tab', { name: 'Free-form' }).click()
  await page.keyboard.type(text)
  const block = page.locator('.ffblock').last()
  await block.getByLabel('Marks').fill(String(marks))
  await block.getByLabel('Marks').press('Enter')
}

test('leave questions out of the key, hide question text and the M/A breakdown', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: '+ New paper' }).click()
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

  // Question 1 comes out of the key; the editor's view dims it but keeps its number.
  await key.getByLabel('Include question 1 in the answer key').uncheck()
  await expect(entries.nth(0)).toHaveClass(/excluded/)
  await expect(entries.nth(0)).toContainText('1.')

  // Hide the question text: the key view drops it too.
  await expect(entries.nth(1)).toContainText('QTWO-TEXT')
  await page.getByLabel('Answer key repeats each question').uncheck()
  await expect(entries.nth(1)).not.toContainText('QTWO-TEXT')
  await page.getByLabel('Answer key shows the M/A marking breakdown').uncheck()

  await expect(page.getByRole('status').first()).toHaveText('Saved', { timeout: 10_000 })
  await page.reload()
  await expect(page.getByLabel('Answer key repeats each question')).not.toBeChecked()
  await expect(page.getByLabel('Answer key shows the M/A marking breakdown')).not.toBeChecked()
  await expect(key.getByLabel('Include question 1 in the answer key')).not.toBeChecked()
  await expect(key.getByLabel('Include question 2 in the answer key')).toBeChecked()

  const printed = await (await page.request.get(`http://localhost:8000/documents/${id}/preview/key`)).text()
  const body = printed.split('</style>').pop()
  expect(body).toContain('ANSWER-TWO')
  expect(body).not.toContain('ANSWER-ONE')
  expect(body).not.toContain('QTWO-TEXT')
  expect(body.match(/counter-reset: q (\d+)/g)).toEqual(['counter-reset: q 1']) // numbered 2, not 1
  const student = await (await page.request.get(`http://localhost:8000/documents/${id}/preview/student`)).text()
  expect(student).toContain('QONE-TEXT')
  expect(student).toContain('QTWO-TEXT')

  // Putting everything back restores the full key.
  await page.getByLabel('Answer key repeats each question').check()
  await key.getByLabel('Include question 1 in the answer key').check()
  await expect(page.getByRole('status').first()).toHaveText('Saved', { timeout: 10_000 })
  const full = await (await page.request.get(`http://localhost:8000/documents/${id}/preview/key`)).text()
  expect(full).toContain('ANSWER-ONE')
  expect(full).toContain('QONE-TEXT')

  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: /Answer key\s*PDF/ }).click(),
  ])
  expect(download.suggestedFilename()).toMatch(/\.pdf$/)
})
