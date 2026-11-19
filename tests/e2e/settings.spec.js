import { test, expect } from '@playwright/test'
import { API } from './helpers.js'

/**
 * Browser acceptance for O1 (EXA-125): the Classic generator is hidden until a teacher turns it
 * on in Settings; the setting is saved on the account (it survives a reload).
 */
test('the Classic generator is hidden until it is turned on in Settings', async ({ page }) => {
  const off = await page.request.put(`${API}/settings`, { data: { classic_generator: false } })
  expect(off.ok()).toBeTruthy()

  await page.goto('/')
  await expect(page.getByRole('link', { name: 'Settings' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Classic generator' })).toHaveCount(0)

  // Going straight to #/classic while it is off says so.
  await page.goto('/#/classic')
  await expect(page.getByRole('heading', { name: 'The Classic generator is turned off' })).toBeVisible()

  await page.goto('/#/settings')
  const sw = page.getByRole('switch', { name: 'Show the Classic generator' })
  await expect(sw).not.toBeChecked()
  await sw.check()
  await expect(page.getByRole('status')).toHaveText('The Classic generator is on.')
  await page.reload()
  await expect(page.getByRole('switch', { name: 'Show the Classic generator' })).toBeChecked()

  await page.getByRole('link', { name: '← Your papers' }).click()
  await page.getByRole('link', { name: 'Classic generator' }).click()
  await expect(page.getByRole('button', { name: 'Generate', exact: true })).toBeVisible()
})
