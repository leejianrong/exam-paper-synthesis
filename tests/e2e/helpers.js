import { expect } from '@playwright/test'

/**
 * Wait until the editor has saved what was just edited.
 *
 * The save chip starts as "Saved", so reading "Saved" straight after an edit can be the stale
 * state from before the edit registered, and a slow CI runner then reloads or navigates with the
 * change still unsent (the list and multi-part specs flaked this way). An edit turns the chip
 * dirty at once and the 1 s debounce keeps it so, so first wait for it to leave "Saved" (short,
 * and skipped if the edit was already saved), then wait for "Saved" again.
 */
export async function settled(page) {
  const chip = page.locator('.bar .chip')
  await chip.filter({ hasNotText: 'Saved' }).waitFor({ timeout: 3000 }).catch(() => {})
  await expect(chip).toHaveText('Saved', { timeout: 15_000 })
}

/**
 * Turn the Classic generator on for the dev owner (O1: it is hidden by default) and open it.
 * `api` is the API origin the page talks to (the dev server, or the CSP spec's one origin).
 */
export async function openClassic(page, { api = 'http://localhost:8000', origin = '' } = {}) {
  const res = await page.request.put(`${api}/settings`, { data: { classic_generator: true } })
  expect(res.ok()).toBeTruthy()
  await page.goto(`${origin}/#/classic`)
}
