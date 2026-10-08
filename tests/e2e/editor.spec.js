import { test, expect } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

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

test('insert questions from my bank (MCQ and table) into a paper', async ({ page }) => {
  // Seed the bank the way a user does: the CLI, as the default `local` owner.
  const bankDb = path.join(os.tmpdir(), 'exam-e2e-bank.sqlite3')
  for (const name of ['psle_2023_mcq', 'psle_2023_table']) {
    execFileSync(
      'uv',
      ['run', 'mathgen', 'bank', 'import', `tests/fixtures/sourced/${name}.json`, '--overwrite'],
      { env: { ...process.env, EXAM_BANK_PATH: bankDb } },
    )
  }

  await page.goto('/')
  await page.getByRole('button', { name: '+ New paper' }).click()
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
  const id = page.url().split('/docs/')[1]
  await page.getByLabel('Paper title').fill('Bank Paper')

  await page.getByRole('button', { name: 'Add question' }).click()
  const dialog = page.getByRole('dialog', { name: 'Add question' })
  await dialog.getByRole('tab', { name: 'From my bank' }).click()
  await expect(dialog.getByTestId('bank-item')).toHaveCount(2)
  // The engine's own print markup is drawn (MCQ options are real list items).
  await expect(dialog.locator('li.option').first()).toBeVisible()
  await dialog.getByTestId('bank-item').first().getByRole('button', { name: 'Use this' }).click()

  const block = page.getByTestId('question-block')
  await expect(block).toHaveCount(1)
  await expect(block.getByText('From my bank')).toBeVisible()
  await expect(block.getByText('Unreviewed')).toBeVisible()
  await expect(block.getByRole('button', { name: 'Make harder' })).toHaveCount(0)
  await expect(block.locator('li.option').first()).toBeVisible()

  // The key region uses the engine key markup for it.
  const key = page.getByRole('region', { name: 'Answer key' })
  await expect(key.locator('.solution').first()).toBeVisible()

  // Add the table question too. The page draws its own numbers with a CSS counter, and
  // counters cross the shadow boundary, so an embedded question must not advance it itself
  // (that numbered the page 1, 3, 5…). Computed counters can't be read back, so assert the
  // cause: no embedded question increments.
  await page.getByRole('button', { name: 'Add question' }).click()
  await dialog.getByRole('tab', { name: 'From my bank' }).click()
  await dialog.getByTestId('bank-item').nth(1).getByRole('button', { name: 'Use this' }).click()
  await expect(page.getByTestId('question-block')).toHaveCount(2)
  await expect(page.getByTestId('question-block').nth(1).locator('table')).toBeVisible()
  const increments = await page
    .locator('.qblock section.question')
    .evaluateAll((els) => els.map((el) => getComputedStyle(el).counterIncrement))
  expect(increments).toEqual(['none', 'none'])
  const own = await page
    .locator('.qblock')
    .evaluateAll((els) => els.map((el) => getComputedStyle(el).counterIncrement))
  expect(own).toEqual(['q 1', 'q 1'])

  // A bank question saves, reloads, and the student copy shows its options but no answers.
  await expect(page.getByRole('status')).toHaveText('Saved', { timeout: 10_000 })
  await page.reload()
  await expect(page.getByTestId('question-block').getByText('From my bank')).toHaveCount(2)
  const student = await (
    await page.request.get(`http://localhost:8000/documents/${id}/preview/student`)
  ).text()
  expect(student).toContain('class="option"')
  expect(student).not.toContain('Answer:')
  const full = await (await page.request.get(`http://localhost:8000/documents/${id}/preview/full`)).text()
  expect(full).toContain('option-correct')
})

test('write a free-form question, set marks, write its answer, reload, preview and export', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: '+ New paper' }).click()
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
  const id = page.url().split('/docs/')[1]
  await page.getByLabel('Paper title').fill('Free-form Paper')

  await addQuestion(page)
  await page.getByRole('button', { name: 'Add question' }).click()
  await page.getByRole('dialog', { name: 'Add question' }).getByRole('tab', { name: 'Free-form' }).click()

  // The caret is already in the new block: just type the question.
  const block = page.locator('.ffblock')
  await expect(block).toHaveCount(1)
  await page.keyboard.type('Ann has 12 sweets and gives away 5. How many are left?')
  await expect(block.locator('.ff-body')).toHaveText('Ann has 12 sweets and gives away 5. How many are left?')
  await block.getByLabel('Marks').fill('3')
  await block.getByLabel('Marks').press('Enter')
  await expect(block.locator('.ff-marks')).toHaveText('[3]')

  // The answer is written in the key region (entry 2: numbering is shared).
  const entry = page.getByRole('region', { name: 'Answer key' }).locator('.entry.freeform')
  await expect(entry).toContainText('2.')
  await entry.locator('.answer').click()
  await page.keyboard.type('12 - 5 = 7. Ann has 7 sweets left.')

  await expect(page.getByRole('status')).toHaveText('Saved', { timeout: 10_000 })
  await page.reload()
  await expect(page.locator('.ffblock')).toContainText('How many are left?')
  await expect(page.locator('.ffblock .ff-marks')).toHaveText('[3]')
  await expect(page.locator('.entry.freeform .answer')).toContainText('Ann has 7 sweets left.')

  const student = await (await page.request.get(`http://localhost:8000/documents/${id}/preview/student`)).text()
  const key = await (await page.request.get(`http://localhost:8000/documents/${id}/preview/key`)).text()
  expect(student).toContain('How many are left?')
  expect(student).toContain('[3]')
  expect(student).not.toContain('Ann has 7 sweets left.')
  expect(key).toContain('Ann has 7 sweets left.')

  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'Answer key PDF' }).click(),
  ])
  expect(download.suggestedFilename()).toMatch(/\.pdf$/)
})

// A real 40x30 PNG (the upload gate checks magic bytes, dimensions and the IEND trailer).
const PNG_B64 = 'iVBORw0KGgoAAAANSUhEUgAAACgAAAAeCAIAAADRv8uKAAAAKklEQVR4nO3NsQ0AAAgDoJ7u5/qCWxcSdrKTis4qFovFYrFYLBaLxeKXAx/uA7qKDGN/AAAAAElFTkSuQmCC'

test('a free-form question with a PNG figure and an equation survives reload and prints', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: '+ New paper' }).click()
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
  const id = page.url().split('/docs/')[1]
  await page.getByLabel('Paper title').fill('Figures Paper')

  await page.getByRole('button', { name: 'Add question' }).click()
  await page.getByRole('dialog', { name: 'Add question' }).getByRole('tab', { name: 'Free-form' }).click()
  await page.keyboard.type('Find the value of ')
  await expect(page.locator('.ffblock .ff-body')).toContainText('Find the value of')

  // Equation: typed LaTeX with a live preview, applied inline.
  await page.getByRole('button', { name: 'Equation', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: 'Equation' })
  await dialog.getByLabel('LaTeX').fill('\\frac{3}{4} \\times 8')
  await expect(dialog.locator('.preview .math-host .katex')).toBeVisible()
  await dialog.getByRole('button', { name: 'Apply' }).click()
  await expect(page.locator('.ffblock .math-node .katex')).toBeVisible()

  // Image: through the toolbar's file chooser.
  await page.getByLabel('Choose image').setInputFiles({
    name: 'figure.png',
    mimeType: 'image/png',
    buffer: Buffer.from(PNG_B64, 'base64'),
  })
  const img = page.locator('.ffblock img.doc-image-img')
  await expect(img).toBeVisible()
  await expect.poll(() => img.evaluate((e) => e.naturalWidth)).toBe(40)

  await page.locator('.ffblock').getByLabel('Marks').fill('3')
  await page.locator('.ffblock').getByLabel('Marks').press('Enter')

  await expect(page.getByRole('status')).toHaveText('Saved', { timeout: 10_000 })
  await page.reload()
  await expect(page.locator('.ffblock .math-node .katex')).toBeVisible()
  await expect(page.locator('.ffblock img.doc-image-img')).toBeVisible()

  // The printed copy has the figure inlined as a data URI and the formula typeset.
  const student = await (await page.request.get(`http://localhost:8000/documents/${id}/preview/student`)).text()
  expect(student).toContain('data:image/png;base64,')
  expect(student).toContain('\\(\\frac{3}{4} \\times 8\\)')
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'Student PDF' }).click(),
  ])
  expect(download.suggestedFilename()).toMatch(/\.pdf$/)
})

test('uploads are validated by content and are private to their owner', async ({ request }) => {
  const api = 'http://localhost:8000'
  const html = Buffer.from('<html><script>alert(1)</script></html>')
  const refused = await request.post(`${api}/assets`, { data: html, headers: { 'X-Filename': 'x.png', 'Content-Type': 'image/png' } })
  expect(refused.status()).toBe(422)

  const ok = await request.post(`${api}/assets`, {
    data: Buffer.from(PNG_B64, 'base64'),
    headers: { 'Content-Type': 'image/png', 'X-Dev-Owner': 'e2e-alice' },
  })
  expect(ok.status()).toBe(201)
  const { id } = await ok.json()
  const mine = await request.get(`${api}/assets/${id}`, { headers: { 'X-Dev-Owner': 'e2e-alice' } })
  expect(mine.status()).toBe(200)
  expect(mine.headers()['x-content-type-options']).toBe('nosniff')
  const theirs = await request.get(`${api}/assets/${id}`, { headers: { 'X-Dev-Owner': 'e2e-bob' } })
  expect(theirs.status()).toBe(404)
})

test('convert a generated question to free-form: text, answer and its figure as an image', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: '+ New paper' }).click()
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
  const id = page.url().split('/docs/')[1]
  await page.getByLabel('Paper title').fill('Convert Paper')
  await addQuestion(page)
  const block = page.getByTestId('question-block')
  await expect(block).toHaveCount(1)
  const original = await block.locator('.part-text, .text').first().innerText().catch(() => '')

  await block.getByRole('button', { name: 'Convert to free-form' }).click()
  const ff = page.locator('.ffblock')
  await expect(ff).toHaveCount(1)
  await expect(page.getByTestId('question-block')).toHaveCount(0)
  // The bar model became an uploaded PNG, and the written answer is editable in the key.
  const img = ff.locator('img.doc-image-img')
  await expect(img).toBeVisible()
  await expect.poll(() => img.evaluate((e) => e.naturalWidth)).toBeGreaterThan(100)
  await expect(ff.locator('.ff-marks')).toHaveText(/\[\d+\]/)
  const entry = page.getByRole('region', { name: 'Answer key' }).locator('.entry.freeform')
  await expect(entry.locator('.answer')).toContainText('Answer:')
  if (original) await expect(ff.locator('.ff-body')).toContainText(original.slice(0, 20))

  // Now it is the teacher's text: edit it freely.
  await ff.locator('.ff-body p').first().click()
  await page.keyboard.press('End')
  await page.keyboard.type(' (edited)')
  await expect(ff.locator('.ff-body')).toContainText('(edited)')

  await expect(page.getByRole('status')).toHaveText('Saved', { timeout: 10_000 })
  const student = await (await page.request.get(`http://localhost:8000/documents/${id}/preview/student`)).text()
  expect(student).toContain('(edited)')
  expect(student).toContain('data:image/png;base64,')
  const key = await (await page.request.get(`http://localhost:8000/documents/${id}/preview/key`)).text()
  expect(key).toContain('Answer:')

})

// A private owner per run: the shared `local` bank is asserted exactly by another test.
const IMPORTER = `e2e-importer-${Date.now().toString(36)}`
test.describe('bank import', () => {
test.use({ extraHTTPHeaders: { 'X-Dev-Owner': IMPORTER } })

test('import canonical JSON into the bank from the editor, review-gated, per-item errors', async ({ page }) => {
  const base = JSON.parse(fs.readFileSync('tests/fixtures/sourced/psle_2023_ratio.json', 'utf8'))
  const stamp = Date.now().toString(36)
  const good = { ...base, id: `sourced:e2e-import-${stamp}` }
  const broken = { ...base, id: `sourced:e2e-broken-${stamp}`, question: { ...base.question, total_marks: undefined } }

  await page.goto('/')
  await page.getByRole('button', { name: '+ New paper' }).click()
  await page.getByRole('button', { name: 'Add question' }).click()
  const dialog = page.getByRole('dialog', { name: 'Add question' })
  await dialog.getByRole('tab', { name: 'From my bank' }).click()
  await dialog.getByRole('button', { name: 'Import…' }).click()

  // Two files in one go: a good question that claims to be reviewed, and a broken one.
  good.validation = { ...good.validation, checks: { ...(good.validation?.checks ?? {}), human_reviewed: true } }
  await dialog.getByLabel('Choose JSON files').setInputFiles([
    { name: 'good.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(good)) },
    { name: 'broken.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(broken)) },
  ])
  await dialog.getByRole('button', { name: 'Import' }).click()
  const results = dialog.getByRole('list', { name: 'Import results' })
  await expect(results.locator('[data-status="imported"]')).toHaveCount(1)
  await expect(results.locator('[data-status="invalid"]')).toHaveCount(1)
  await expect(results.locator('[data-status="invalid"]')).toContainText('total_marks')

  // Importing the same file again reports a duplicate instead of overwriting.
  await dialog.getByLabel('Choose JSON files').setInputFiles([
    { name: 'good.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(good)) },
  ])
  await dialog.getByRole('button', { name: 'Import' }).click()
  await expect(results.locator('[data-status="duplicate"]')).toHaveCount(1)

  // Back in the bank it is listed, and it arrived unreviewed whatever the file claimed.
  await dialog.getByRole('button', { name: 'Back to bank' }).click()
  const item = dialog.getByTestId('bank-item').filter({ has: page.locator('.tag', { hasText: 'Unreviewed' }) })
  await expect(item.first()).toBeVisible()
  const bank = await (await page.request.get('http://localhost:8000/bank')).json()
  const stored = bank.items.find((i) => i.id === good.id)
  expect(stored).toBeTruthy()
  expect(stored.reviewed).toBe(false)
})
})

test('typing "1. " makes a numbered list that still saves (editor-only attributes are stripped)', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: '+ New paper' }).click()
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
  await page.getByRole('button', { name: 'Add question' }).click()
  await page.getByRole('dialog', { name: 'Add question' }).getByRole('tab', { name: 'Free-form' }).click()
  await page.keyboard.type('Which are prime?')
  await page.keyboard.press('Enter')
  await page.keyboard.type('1. Two')
  await expect(page.locator('.ffblock .ff-body ol')).toBeVisible()
  const entry = page.getByRole('region', { name: 'Answer key' }).locator('.entry.freeform')
  await entry.locator('.answer').click()
  await page.keyboard.type('7. Seven')
  await expect(entry.locator('.answer ol')).toBeVisible()
  await expect(page.getByRole('status')).toHaveText('Saved', { timeout: 10_000 })
})
