import { test, expect } from '@playwright/test'
import { API } from './ports.js'

/**
 * Browser acceptance for O2 (EXA-126) and the list cleanup (EXA-166): make a folder on "Your
 * papers", move a paper into it from the paper's ⋯ menu, collapse the folder (remembered over a
 * reload), search, then delete the folder from its own menu: the paper is unfiled, never deleted.
 * The store is shared with the other specs, so names are unique.
 */

test('create a folder, move a paper in, collapse and search, delete the folder: the paper is unfiled', async ({ page }) => {
  const stamp = Date.now()
  const title = `E2E folders ${stamp} Booklet B`
  const name = `E2E set ${stamp}`
  const created = await page.request.post(`${API}/documents`, { data: { template: 'p1_booklet_b', title } })
  expect(created.ok()).toBeTruthy()
  const { id } = await created.json()

  await page.goto('/')
  await page.getByRole('button', { name: '+ New', exact: true }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'New folder', exact: true }).click()
  await page.getByRole('form', { name: 'New folder' }).getByRole('textbox', { name: 'Folder name' }).fill(name)
  await page.getByRole('button', { name: 'Create folder' }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  const folder = page.getByRole('region', { name, exact: true })
  await expect(folder).toBeVisible()
  await expect(folder.getByText('No papers here yet')).toBeVisible()
  // The owner asked for no exam-set ticks on folders (EXA-166).
  await expect(folder.getByText('Booklet A', { exact: true })).toHaveCount(0)

  // Move the paper in from its row's ⋯ menu.
  const row = page.locator('li.row', { hasText: title })
  await row.getByRole('button', { name: `Actions for “${title}”` }).click()
  await page.getByRole('menuitem', { name: 'Move to folder…' }).click()
  const move = page.getByRole('dialog', { name: 'Move to folder' })
  await move.getByRole('radio', { name, exact: true }).check()
  await move.getByRole('button', { name: 'Move', exact: true }).click()
  await expect(folder.getByRole('link', { name: new RegExp(title) })).toBeVisible()

  // Moving is not an edit: the paper's version is unchanged.
  const moved = await (await page.request.get(`${API}/documents/${id}`)).json()
  expect(moved.folder_id).toBeTruthy()
  expect(moved.version).toBe(1)

  // Collapse the folder: it stays collapsed after a reload, and a search still finds the paper.
  const toggle = folder.getByRole('button', { name, exact: true })
  await toggle.click()
  await expect(toggle).toHaveAttribute('aria-expanded', 'false')
  await expect(folder.getByRole('link', { name: new RegExp(title) })).toHaveCount(0)
  await page.reload()
  await expect(folder.getByRole('button', { name, exact: true })).toHaveAttribute('aria-expanded', 'false')
  await page.getByRole('searchbox', { name: 'Search papers' }).fill(`folders ${stamp}`)
  await expect(folder.getByRole('link', { name: new RegExp(title) })).toBeVisible()
  await expect(page.locator('li.row')).toHaveCount(1)
  await page.getByRole('searchbox', { name: 'Search papers' }).press('Escape')
  await folder.getByRole('button', { name, exact: true }).click()
  await expect(folder.getByRole('link', { name: new RegExp(title) })).toBeVisible()

  // Delete the folder from its menu: it asks first and says the paper stays.
  await folder.getByRole('button', { name: `Actions for folder “${name}”` }).click()
  await page.getByRole('menuitem', { name: 'Delete folder…' }).click()
  const confirm = page.getByRole('alertdialog', { name: `Delete the folder “${name}”?` })
  await expect(confirm).toContainText('Its 1 paper will move to Unfiled. No paper is deleted.')
  await confirm.getByRole('button', { name: 'Delete folder', exact: true }).click()
  await expect(page.getByRole('region', { name, exact: true })).toHaveCount(0)
  await expect(page.locator('li.row', { hasText: title })).toHaveCount(1)
  await expect(page.locator('section.folder li.row', { hasText: title })).toHaveCount(0)

  const after = await (await page.request.get(`${API}/documents/${id}`)).json()
  expect(after.folder_id).toBeNull()
  await page.request.delete(`${API}/documents/${id}`)
})

test('+ New → Exam set → a new folder → empty starters: the folder holds the three papers', async ({ page }) => {
  // O3 (EXA-127). Exam set is the first choice and has focus (EXA-166).
  const name = `E2E exam set ${Date.now()}`
  await page.goto('/')
  await page.getByRole('button', { name: '+ New', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog.getByRole('button', { name: 'Exam set', exact: true })).toBeFocused()
  await dialog.getByRole('button', { name: 'Exam set', exact: true }).click()
  await expect(dialog.getByRole('radio', { name: 'A new folder' })).toBeChecked()
  await dialog.getByRole('textbox', { name: 'Folder name' }).fill(name)
  await dialog.getByRole('button', { name: 'Next' }).click()
  await dialog.getByRole('button', { name: 'Empty starters' }).click()
  await expect(dialog).toHaveCount(0)

  const folder = page.getByRole('region', { name, exact: true })
  await expect(folder).toBeVisible()
  await expect(folder.getByRole('button', { name, exact: true })).toBeFocused()
  await expect(folder.locator('li.row')).toHaveCount(3)

  // Still there after a reload, read from the server.
  await page.reload()
  await expect(folder.locator('li.row')).toHaveCount(3)

  // Tidy the shared store: the papers, then the folder.
  const docs = (await (await page.request.get(`${API}/documents`)).json()).documents
  const folders = (await (await page.request.get(`${API}/folders`)).json()).folders
  const id = folders.find((f) => f.name === name).id
  const mine = docs.filter((d) => d.folder_id === id)
  expect(mine.map((d) => d.paper_part).sort()).toEqual(['booklet_a', 'booklet_b', 'paper_2'])
  for (const d of mine) await page.request.delete(`${API}/documents/${d.id}`)
  await page.request.delete(`${API}/folders/${id}`)
})

test('a paper’s ⋯ menu by keyboard: rename it, make a copy', async ({ page }) => {
  const stamp = Date.now()
  const title = `E2E menu ${stamp}`
  const created = await page.request.post(`${API}/documents`, { data: { template: 'p2', title } })
  const { id } = await created.json()

  await page.goto('/')
  const actions = (t) => page.getByRole('button', { name: `Actions for “${t}”` })
  await page.getByRole('link', { name: new RegExp(title) }).focus()
  await page.keyboard.press('Shift+F10')
  const menu = page.getByRole('menu', { name: title })
  await expect(menu.getByRole('menuitem', { name: 'Open' })).toBeFocused()
  await page.keyboard.press('ArrowDown')
  await page.keyboard.press('Enter')
  const input = page.getByRole('textbox', { name: 'Paper title' })
  await expect(input).toBeFocused()
  await input.fill(`${title} renamed`)
  await input.press('Enter')
  await expect(actions(`${title} renamed`)).toBeFocused()
  expect((await (await page.request.get(`${API}/documents/${id}`)).json()).title).toBe(`${title} renamed`)

  await page.keyboard.press('ArrowDown')
  await page.getByRole('menuitem', { name: 'Make a copy' }).press('Enter')
  await expect(page.getByRole('link', { name: new RegExp(`Copy of ${title} renamed`) })).toBeVisible()

  const docs = (await (await page.request.get(`${API}/documents`)).json()).documents
  for (const d of docs.filter((x) => x.title.includes(title))) await page.request.delete(`${API}/documents/${d.id}`)
})
