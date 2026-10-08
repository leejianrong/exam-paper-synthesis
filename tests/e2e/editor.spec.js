import { test, expect } from '@playwright/test'

/**
 * Browser acceptance for the W1 WYSIWYG editor: create a paper, add generated
 * questions through the "+" picker, edit one (make harder, rename the people), reload and
 * find everything persisted, then check the student vs full renderings and a PDF export.
 * Needs the API started with EXAM_DEV_AUTH=1 (playwright.config.js does this).
 */

async function addQuestion(page, { topic = 'Ratio', difficulty = 'Medium' } = {}) {
  await page.getByRole('button', { name: 'Add question' }).click()
  const dialog = page.getByRole('dialog', { name: 'Add question' })
  await dialog.getByLabel('Topic').selectOption({ label: topic })
  await dialog.getByLabel('Difficulty').selectOption({ label: difficulty })
  await dialog.getByRole('button', { name: /^Generate/ }).click()
  await expect(dialog.getByTestId('candidate')).toHaveCount(3)
  await dialog.getByRole('button', { name: 'Use this' }).first().click()
  await expect(dialog).toBeHidden()
}

test('build a paper, edit questions, reload, preview and export', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Your papers' })).toBeVisible()
  await page.getByRole('button', { name: '+ New paper' }).click()
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
  const id = page.url().split('/docs/')[1]

  await page.getByLabel('Paper title').fill('E2E Ratio Paper')

  await addQuestion(page)
  await addQuestion(page, { topic: 'Speed', difficulty: 'Easy' })
  const blocks = page.getByTestId('question-block')
  await expect(blocks).toHaveCount(2)

  // Make the first question harder (ratio_medium -> ratio_hard).
  const firstBefore = await blocks.first().innerText()
  await blocks.first().getByRole('button', { name: 'Make harder' }).click()
  await expect(async () => {
    expect(await blocks.first().innerText()).not.toBe(firstBefore)
  }).toPass()

  // Rename the people in the second question.
  await blocks.nth(1).getByRole('button', { name: 'Edit names' }).click()
  const nameField = blocks.nth(1).getByLabel('Name', { exact: true })
  await nameField.fill('Zainab')
  await blocks.nth(1).getByRole('button', { name: 'Apply' }).click()
  await expect(blocks.nth(1)).toContainText('Zainab')

  // Answer key lists both questions.
  const key = page.getByRole('region', { name: 'Answer key' })
  await expect(key.locator('.entry')).toHaveCount(2)

  // Autosave settles, and everything survives a reload.
  await expect(page.getByRole('status')).toHaveText('Saved', { timeout: 10_000 })
  await page.reload()
  await expect(page.getByLabel('Paper title')).toHaveValue('E2E Ratio Paper')
  await expect(page.getByTestId('question-block')).toHaveCount(2)
  await expect(page.getByTestId('question-block').nth(1)).toContainText('Zainab')

  // True-print renderings: the student copy has no answers, the full copy has the key.
  const student = await (await page.request.get(`http://localhost:8000/documents/${id}/preview/student`)).text()
  const full = await (await page.request.get(`http://localhost:8000/documents/${id}/preview/full`)).text()
  expect(student).not.toContain('Answer:')
  expect(student).toContain('Zainab')
  expect(full).toContain('Answer Key')
  expect(full).toContain('Answer:')

  // In-editor preview opens the real print HTML.
  await page.getByRole('button', { name: 'Preview' }).click()
  const frame = page.frameLocator('iframe[title="Print preview"]')
  await expect(frame.getByText('Answer Key').first()).toBeVisible()
  await page.getByRole('button', { name: 'Close preview' }).click()

  // PDF export downloads a real .pdf.
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'Student PDF' }).click(),
  ])
  expect(download.suggestedFilename()).toMatch(/\.pdf$/)
})

test('the documents list shows, opens and deletes a paper', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: '+ New paper' }).click()
  await page.getByLabel('Paper title').fill('Throwaway')
  await expect(page.getByRole('status')).toHaveText('Saved', { timeout: 10_000 })
  await page.getByRole('link', { name: '← Papers' }).click()
  const row = page.locator('li.doc', { hasText: 'Throwaway' })
  await expect(row).toBeVisible()
  await row.getByRole('button', { name: 'Delete' }).click()
  await row.getByRole('button', { name: 'Confirm delete' }).click()
  await expect(page.locator('li.doc', { hasText: 'Throwaway' })).toHaveCount(0)
})
