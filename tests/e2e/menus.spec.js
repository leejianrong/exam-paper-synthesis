import { test, expect } from '@playwright/test'
import { headerMenu, newBlankPaper, selectQuestion } from './helpers.js'

/**
 * EXA-163: the command palette runs a question's action by name, and View > Show side panel gives
 * the page its full A4 width on a 1024 px laptop (the panel left it narrower before).
 */
async function addQuestion(page) {
  await page.keyboard.press('Control+Enter')
  const dialog = page.getByRole('dialog', { name: 'Add question' })
  await dialog.getByLabel('Topic').selectOption({ label: 'Ratio' })
  await dialog.getByLabel('Difficulty').selectOption({ label: 'Medium' })
  await dialog.getByRole('button', { name: /^Generate/ }).click()
  await expect(dialog.getByTestId('candidate')).toHaveCount(3)
  await dialog.getByRole('button', { name: 'Use this' }).first().click()
  await expect(dialog).toBeHidden()
}

test('Ctrl+K, "harder", Enter makes the selected question harder', async ({ page }) => {
  await page.goto('/')
  await newBlankPaper(page)
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
  await page.locator('.surface .ProseMirror').click()
  await addQuestion(page) // Ctrl+Enter opened the picker
  const block = page.getByTestId('question-block').first()
  const before = await block.innerText()

  const host = await selectQuestion(block)
  await page.keyboard.press('Control+k')
  const box = page.getByRole('combobox', { name: 'Find a command' })
  await expect(box).toBeFocused()
  await box.fill('harder')
  const options = page.getByRole('listbox', { name: 'Commands' }).getByRole('option')
  await expect(options).toHaveCount(1)
  await expect(options.first()).toContainText('Make harder')
  await page.keyboard.press('Enter')
  await expect(box).toBeHidden()
  await expect(async () => expect(await block.innerText()).not.toBe(before)).toPass()
  await expect(host).toBeVisible()
})

test('hiding the side panel gives the page its full A4 width at 1024 px, and it stays hidden', async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 800 })
  await page.goto('/')
  await newBlankPaper(page)
  await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
  const panel = page.getByRole('complementary', { name: 'Side panel' })
  await expect(panel).toBeVisible()
  const a4 = await page.evaluate(() => {
    const probe = document.createElement('div')
    probe.style.width = '210mm'
    document.body.append(probe)
    const w = probe.getBoundingClientRect().width
    probe.remove()
    return w
  })
  const pageWidth = () => page.locator('.page').evaluate((el) => el.getBoundingClientRect().width)
  expect(await pageWidth()).toBeLessThan(a4 - 1)

  const view = await headerMenu(page, 'View')
  await view.getByRole('menuitemcheckbox', { name: 'Show side panel' }).click()
  await expect(panel).toHaveCount(0)
  expect(Math.abs((await pageWidth()) - a4)).toBeLessThan(1)

  await page.reload()
  await expect(page.locator('.page')).toBeVisible()
  await expect(panel).toHaveCount(0)
  await page.keyboard.press('Control+\\')
  await expect(panel).toBeVisible()
})
