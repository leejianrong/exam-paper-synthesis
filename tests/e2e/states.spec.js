import { test, expect } from '@playwright/test'
import { API } from './ports.js'

/**
 * Browser acceptance for EXA-165 (UI states): an unknown paper id is a plain page that says
 * what happened and leads back to Your papers, never an empty editor that claims "Saved"; and
 * a list the server can't give says so in words, with Try again.
 */

test('an unknown paper is a page of its own, with the way back to Your papers', async ({ page }) => {
  await page.goto('/#/docs/no-such-paper-exa165')
  await expect(page.getByRole('heading', { name: "This paper doesn't exist or was deleted" })).toBeVisible()
  // no editor behind it: no title box, no save chip, no toolbar
  await expect(page.getByRole('textbox', { name: 'Paper title' })).toBeHidden()
  await expect(page.locator('.ehead')).toBeHidden()
  await expect(page.getByText('Saved', { exact: true })).toBeHidden()
  await expect(page.getByText(/404|not found/i)).toHaveCount(0)

  await page.getByRole('link', { name: 'Back to Your papers' }).click()
  await expect(page.getByRole('heading', { name: 'Your papers' })).toBeVisible()
})

test("a list the server can't give says so in words, and Try again loads it", async ({ page }) => {
  const title = `E2E states ${Date.now()}`
  const created = await page.request.post(`${API}/documents`, { data: { title } })
  expect(created.ok()).toBeTruthy()

  let fail = true
  await page.route(/\/documents$/, (route) =>
    fail && route.request().method() === 'GET'
      ? route.fulfill({ status: 500, contentType: 'application/json', body: '{"detail":"boom"}' })
      : route.fallback(),
  )
  await page.goto('/')
  const alert = page.getByRole('alert')
  await expect(alert).toContainText("Couldn't load your papers. Something went wrong on our side.")
  await expect(alert).not.toContainText('500')
  await expect(alert).not.toContainText('boom')

  fail = false
  await alert.getByRole('button', { name: 'Try again' }).click()
  await expect(page.getByRole('link', { name: new RegExp(title) })).toBeVisible()
  await expect(page.getByRole('alert')).toHaveCount(0)
})
