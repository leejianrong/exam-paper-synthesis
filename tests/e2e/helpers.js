import { expect } from '@playwright/test'

/** The API origin the e2e servers run on (playwright.config.js; E2E_API_PORT moves it). */
export const API = `http://localhost:${process.env.E2E_API_PORT || 8000}`
/** The CSP spec's one-origin production-shaped server. */
export const CSP_ORIGIN = `http://localhost:${process.env.E2E_CSP_PORT || 8001}`

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
  const chip = page.locator('.ehead .saved')
  await chip.filter({ hasNotText: 'Saved' }).waitFor({ timeout: 3000 }).catch(() => {})
  await expect(chip).toHaveText('Saved', { timeout: 15_000 })
}

/**
 * Turn the Classic generator on for the dev owner (O1: it is hidden by default) and open it.
 * `api` is the API origin the page talks to (the dev server, or the CSP spec's one origin).
 */
export async function openClassic(page, { api = API, origin = '' } = {}) {
  const res = await page.request.put(`${api}/settings`, { data: { classic_generator: true } })
  expect(res.ok()).toBeTruthy()
  await page.goto(`${origin}/#/classic`)
}

/**
 * O3: "+ New" opens the wizard. These walk it for the specs that used to click the list's
 * "+ New paper", template and "Generate a paper" controls; each lands in the editor.
 */
async function openNew(page) {
  await page.getByRole('button', { name: '+ New', exact: true }).click()
  return page.getByRole('dialog')
}

export async function newBlankPaper(page) {
  const dialog = await openNew(page)
  await dialog.getByRole('button', { name: 'Blank paper', exact: true }).click()
}

/**
 * A starter paper (cover and sections, no questions): + New → Single paper → Start it empty.
 * `label` is the template's label from GET /papers, e.g. "Paper 2", "Paper 1 · Booklet B".
 */
export async function newFromTemplate(page, label) {
  const dialog = await openNew(page)
  await dialog.getByRole('button', { name: 'Single paper', exact: true }).click()
  await dialog.getByRole('button', { name: label, exact: true }).click()
  await dialog.getByRole('button', { name: 'Start it empty', exact: true }).click()
}

export async function generateSinglePaper(page, label, level) {
  const dialog = await openNew(page)
  await dialog.getByRole('button', { name: 'Single paper', exact: true }).click()
  await dialog.getByRole('button', { name: label, exact: true }).click()
  await dialog.getByRole('button', { name: `Generate at ${level}`, exact: true }).click()
}

/** EXA-160: choose a PDF from the editor header's Export ▾ menu. */
export async function exportPdf(page, item) {
  await page.getByRole('button', { name: 'Export', exact: true }).click()
  await page.getByRole('menuitem', { name: item, exact: true }).click()
}

/** EXA-160: the formatting toolbar's ⋯ menu (cover page, blank page, page break for now). */
export async function moreTools(page) {
  await page.getByRole('button', { name: 'More tools', exact: true }).click()
  return page.getByRole('menu', { name: 'More tools' })
}

/** EXA-160: paper settings live on the side panel's Paper tab (a question you click brings its
 *  own tab forward). */
export async function paperTab(page) {
  await page.getByRole('tab', { name: 'Paper', exact: true }).click()
}
