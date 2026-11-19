import { test, expect } from '@playwright/test'
import { generateSinglePaper, questionHost, questionMenu, questionPill } from './helpers.js'
import { API } from './ports.js'

/**
 * Browser acceptance for P8d: on a generated paper, swap questions (another topic, write my
 * own), lock one, and "Regenerate unlocked" keeps the locked question while the sections stay
 * at their marks targets. Needs the API with EXAM_DEV_AUTH (playwright.config.js).
 */
test('swap, lock and regenerate a generated P6 Paper 2', async ({ page }) => {
  await page.goto('/')
  await generateSinglePaper(page, 'Paper 2', 'P6')
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
  const id = page.url().split('/docs/')[1]
  const sectionA = page.locator('.section-block').nth(0).locator('.section-summary')
  await expect(sectionA).toHaveText('Questions 1–5 · 10 / 10 marks')

  const blocks = page.getByTestId('question-block')
  // 17 questions: Section B has 10 multi-part and 2 stand-ins (EXA-143, EXA-148, EXA-150, EXA-154)
  await expect(blocks.nth(16)).toBeVisible()
  expect(await blocks.count()).toBe(17)

  // Lock question 1.
  const first = blocks.nth(0)
  await (await questionPill(first, 'Lock')).click()
  await expect(await questionPill(first, 'Lock')).toHaveAttribute('aria-pressed', 'true')
  // At rest a locked question shows only a padlock badge; its swaps leave the menu.
  await expect(first.getByTitle('Locked: kept when you regenerate', { exact: true })).toBeVisible()
  await expect(questionHost(first)).toHaveAttribute('aria-label', /, locked$/)
  await questionHost(first).getByRole('button', { name: /^More actions/ }).click()
  await expect(questionHost(first).getByRole('menuitem', { name: 'Another topic' })).toHaveCount(0)
  await expect(questionHost(first).getByRole('menuitem', { name: 'Unlock' })).toBeVisible()
  await page.keyboard.press('Escape')
  // The question itself (its stem), compared as DOM text content: innerText would also carry
  // the block's form controls (working-space and unit menus) laid out line by line. Always
  // read it with textContent(), never toHaveText(): toHaveText also reads the KaTeX shadow
  // roots, so a stem with maths ("$x") would read "$xxxx" there and never match.
  const stemOf = (block) => block.locator('.qbody')
  const textOf = (block) => stemOf(block).textContent()
  const lockedStem = await textOf(first)

  // Question 2: "Replace with my own question" leaves a 2-mark placeholder; the section stays
  // at 10 marks.
  const second = blocks.nth(1)
  await questionMenu(second, 'Replace with my own question')
  await expect(page.getByTestId('placeholders-left')).toHaveText('1 placeholder to write')
  await expect(page.locator('.ff-placeholder-hint:visible')).toHaveText(/write a 2-mark short-answer question/)
  await expect(sectionA).toHaveText('Questions 1–5 · 10 / 10 marks')

  // Question 3 (now the second generated block): another topic, same marks.
  const third = blocks.nth(1)
  const before = await textOf(third)
  await questionMenu(third, 'Another topic')
  await expect(page.getByText(/Swapped in a 2-mark/)).toBeVisible()
  await expect.poll(() => textOf(third)).not.toBe(before)
  await expect(sectionA).toHaveText('Questions 1–5 · 10 / 10 marks')

  // The R shortcut on a focused question is "Another like this" (EXA-161).
  const beforeR = await textOf(third)
  await questionHost(third).focus()
  await page.keyboard.press('r')
  await expect.poll(() => textOf(third)).not.toBe(beforeR)
  await expect(sectionA).toHaveText('Questions 1–5 · 10 / 10 marks')

  // Regenerate: the locked question stays, the placeholder is filled, targets hold.
  const api = async () => (await page.request.get(`${API}/documents/${id}`)).json()
  const lockedBlock = (doc) => doc.document.content.content.filter((n) => n.attrs && n.attrs.locked === true)
  const lockedBefore = lockedBlock(await api())
  expect(lockedBefore).toHaveLength(1)
  // EXA-160: in the side panel, confirmed in a dialog that names what happens.
  await page.getByRole('tab', { name: 'Paper', exact: true }).click()
  await page.getByRole('button', { name: /^Regenerate 16 unlocked/ }).click()
  const confirm = page.getByRole('alertdialog', { name: 'Regenerate unlocked questions?' })
  await expect(confirm).toContainText('Replaces 16 unlocked questions. 1 locked question stays.')
  await confirm.getByRole('button', { name: 'Regenerate', exact: true }).click()
  await expect(page.getByText(/Regenerated 1[67] questions; kept 1/)).toBeVisible()
  await expect(page.getByTestId('placeholders-left')).toHaveCount(0)
  await expect.poll(() => textOf(blocks.nth(0))).toBe(lockedStem)
  await expect(sectionA).toHaveText('Questions 1–5 · 10 / 10 marks')
  await expect(page.locator('.section-block').nth(1).locator('.section-summary')).toHaveText(
    /Questions 6–1[78] · 45 \/ 45 marks/,
  )

  // What the server stored is what the editor shows (the lock survives a reload).
  await page.reload()
  await expect(page.getByTestId('question-block').nth(0).getByTitle('Locked: kept when you regenerate', { exact: true })).toHaveCount(1)
  const lockedAfter = lockedBlock(await api())
  expect(lockedAfter).toHaveLength(1)
  expect(lockedAfter[0].attrs.question.id).toBe(lockedBefore[0].attrs.question.id)
  expect(lockedAfter[0].attrs.question.question).toEqual(lockedBefore[0].attrs.question.question)
})
