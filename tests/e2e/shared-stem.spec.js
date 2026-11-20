import { test, expect } from '@playwright/test'
import { settled, newBlankPaper, insertMenu } from './helpers.js'
import { API } from './ports.js'

/**
 * EXA-90: a shared stem from the Insert menu. Two own questions, the caret in the first, Insert >
 * Shared stem: the stem goes above it and shares it with the next one; its lead line is derived
 * from their numbers. The buttons let a question go and take it back; the paper prints it.
 */
test('insert a shared stem, change its questions, reload and print it', async ({ page }) => {
  await page.goto('/')
  await newBlankPaper(page)
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
  const id = page.url().split('/docs/')[1]

  for (const text of ['Find the cost of 3 letters.', 'Find the cost of a 250 g parcel.']) {
    await page.getByRole('button', { name: 'Add question' }).click()
    await page.getByRole('dialog', { name: 'Add question' }).getByRole('tab', { name: 'Write my own' }).click()
    await page.keyboard.type(text)
  }
  await page.locator('.ffblock .ff-body').first().click()
  await (await insertMenu(page)).getByRole('menuitem', { name: 'Shared stem' }).click()
  await page.keyboard.type('The table shows the cost of postage.')

  const stem = page.locator('.group-stem-block')
  await expect(stem.locator('.group-lead')).toHaveText('Use the information below to answer Questions 1 and 2.')
  await expect(page.locator('.ffblock.in-group')).toHaveCount(2)

  await stem.getByRole('button', { name: 'Let the last question go from the stem' }).click()
  await expect(stem.locator('.group-lead')).toHaveText('Use the information below to answer Question 1.')
  await stem.getByRole('button', { name: 'Take in the next question' }).click()
  await expect(stem.locator('.group-count')).toHaveText('2 questions')

  await settled(page)
  await page.reload()
  await expect(page.locator('.group-stem-block .group-lead')).toHaveText(
    'Use the information below to answer Questions 1 and 2.',
  )
  const student = await (await page.request.get(`${API}/documents/${id}/preview/student`)).text()
  expect(student).toContain('Use the information below to answer Questions 1 and 2.')
  expect(student).toContain('The table shows the cost of postage.')
})
