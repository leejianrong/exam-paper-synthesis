import { expect } from '@playwright/test'
import { API } from './ports.js'

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
  // A page already open read its settings at load; a hash change keeps them: load them again.
  await page.reload()
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
  await page.getByRole('menu', { name: 'Export' }).getByRole('menuitem', { name: item, exact: true }).click()
}

/** EXA-163: open a menu of the header's menu row (Paper, Insert, View, Help) and return it. */
export async function headerMenu(page, name) {
  await page.getByRole('menubar', { name: 'Paper menus' }).getByRole('menuitem', { name, exact: true }).click()
  return page.getByRole('menu', { name, exact: true })
}

/** The Insert menu: cover page, blank or rough-work page, page break, image, equation. */
export const insertMenu = (page) => headerMenu(page, 'Insert')

/** EXA-160: paper settings live on the side panel's Paper tab (a question you click brings its
 *  own tab forward). */
export async function paperTab(page) {
  await page.getByRole('tab', { name: 'Paper', exact: true }).click()
}

/**
 * A question block's controls (EXA-161) show once it is selected: focus the block (the
 * node view around `[data-testid=question-block]`), then use its pill or its ⋯ menu.
 */
export const questionHost = (block) =>
  block.locator('xpath=ancestor-or-self::*[contains(concat(" ", normalize-space(@class), " "), " qblock ")][1]')

export async function selectQuestion(block) {
  const host = questionHost(block)
  await host.focus()
  await expect(host.locator('.qpill')).toBeVisible()
  return host
}

/** A button in the selected question's pill ("Another like this", "Lock", …). */
export async function questionPill(block, name) {
  const host = await selectQuestion(block)
  return host.locator('.qpill').getByRole('button', { name, exact: true })
}

/** Choose a row from the question's ⋯ menu. */
export async function questionMenu(block, name) {
  const host = await selectQuestion(block)
  await host.getByRole('button', { name: /^More actions/ }).click()
  await host.getByRole('menuitem', { name, exact: true }).click()
}
