import { test, expect } from '@playwright/test'

/**
 * Browser acceptance for EXA-170 (sign-in page). The e2e API runs the dev stub, so nobody is
 * ever signed out: the spec answers `/auth/me` with a 401 to reach the page. `/auth/providers`
 * is the real one (no OAuth app configured, dev stub on), then a stand-in with two providers.
 */

test.beforeEach(async ({ page }) => {
  let signedOut = true
  await page.route(/\/auth\/me$/, (route) =>
    signedOut ? route.fulfill({ status: 401, contentType: 'application/json', body: '{"detail":"x"}' }) : route.fallback(),
  )
  await page.exposeFunction('e2eSignIn', () => {
    signedOut = false
  })
})

test('names the product, says why a sign-in failed, and lets a developer in', async ({ page }) => {
  await page.goto('/#/login?error=state')
  await expect(page).toHaveTitle('Exam papers')
  await expect(page.getByRole('heading', { level: 1, name: 'Exam papers' })).toBeVisible()
  await expect(page.getByRole('alert')).toHaveText('That sign-in took too long or was started in another tab. Sign in again.')
  await expect(page.getByText('Development only')).toBeVisible()

  await page.evaluate(() => window.e2eSignIn())
  await page.getByRole('button', { name: 'Continue without signing in' }).click()
  await expect(page.getByRole('heading', { name: 'Your papers' })).toBeVisible()
})

test("shows each configured provider's button, in keyboard order, at phone width", async ({ page }) => {
  await page.route(/\/auth\/providers$/, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ providers: [{ name: 'google', label: 'Google' }, { name: 'microsoft', label: 'Microsoft' }], dev: false }),
    }),
  )
  await page.setViewportSize({ width: 390, height: 800 })
  await page.goto('/')
  const google = page.getByRole('link', { name: 'Sign in with Google' })
  await expect(google).toBeVisible()
  await expect(page.getByRole('link', { name: /GitHub/ })).toHaveCount(0)
  await expect(page.getByText('Development only')).toHaveCount(0)

  await page.keyboard.press('Tab')
  await expect(google).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: 'Sign in with Microsoft' })).toBeFocused()

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
  expect(overflow).toBeLessThanOrEqual(0)
})
