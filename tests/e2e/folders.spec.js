import { test, expect } from '@playwright/test'
import { API } from './ports.js'

/**
 * Browser acceptance for O2 (EXA-126): make a folder on "Your papers", move a paper into it from
 * the paper's Move menu, see the folder's exam-set chip fill, then delete the folder: the paper
 * is unfiled, never deleted. The store is shared with the other specs, so names are unique.
 */

test('create a folder, move a paper in, see its chip, delete the folder: the paper is unfiled', async ({ page }) => {
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
  await expect(folder.getByText('No papers in this folder yet')).toBeVisible()
  await expect(folder.locator('[data-part="booklet_b"]')).not.toHaveClass(/\bon\b/)

  // Move the paper in from its row's menu.
  const row = page.locator('li.doc', { hasText: title })
  await row.getByRole('button', { name: `Move “${title}” to a folder` }).click()
  await page.getByRole('menu', { name: 'Move to' }).getByRole('menuitemradio', { name, exact: true }).click()
  await expect(folder.getByRole('link', { name: new RegExp(title) })).toBeVisible()
  await expect(folder.locator('[data-part="booklet_b"]')).toHaveClass(/\bon\b/)
  await expect(folder.locator('[data-part="booklet_a"]')).not.toHaveClass(/\bon\b/)

  // Moving is not an edit: the paper's version is unchanged.
  const moved = await (await page.request.get(`${API}/documents/${id}`)).json()
  expect(moved.folder_id).toBeTruthy()
  expect(moved.version).toBe(1)

  // Survives a reload.
  await page.reload()
  await expect(folder.locator('[data-part="booklet_b"]')).toHaveClass(/\bon\b/)

  // Delete the folder: it asks first and says the paper stays.
  await folder.getByRole('button', { name: `Delete folder “${name}”` }).click()
  await expect(folder.getByRole('group', { name: `Delete folder “${name}”?` })).toContainText(
    'Its 1 paper will move to Unfiled. No paper is deleted.',
  )
  await folder.getByRole('button', { name: 'Delete folder', exact: true }).click()
  await expect(page.getByRole('region', { name, exact: true })).toHaveCount(0)
  await expect(page.locator('li.doc', { hasText: title })).toHaveCount(1)
  await expect(page.locator('section.folder li.doc', { hasText: title })).toHaveCount(0)

  const after = await (await page.request.get(`${API}/documents/${id}`)).json()
  expect(after.folder_id).toBeNull()
  await page.request.delete(`${API}/documents/${id}`)
})

test('+ New → Exam set → a new folder → empty starters: the folder holds the three papers', async ({ page }) => {
  // O3 (EXA-127). Each part's chip is filled from the server's paper_part (the cover page).
  const name = `E2E exam set ${Date.now()}`
  await page.goto('/')
  await page.getByRole('button', { name: '+ New', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByRole('button', { name: 'Exam set', exact: true }).click()
  await expect(dialog.getByRole('radio', { name: 'A new folder' })).toBeChecked()
  await dialog.getByRole('textbox', { name: 'Folder name' }).fill(name)
  await dialog.getByRole('button', { name: 'Next' }).click()
  await dialog.getByRole('button', { name: 'Empty starters' }).click()
  await expect(dialog).toHaveCount(0)

  const folder = page.getByRole('region', { name, exact: true })
  await expect(folder).toBeVisible()
  await expect(folder.getByRole('heading', { name, exact: true })).toBeFocused()
  await expect(folder.locator('li.doc')).toHaveCount(3)
  for (const part of ['booklet_a', 'booklet_b', 'paper_2']) {
    await expect(folder.locator(`[data-part="${part}"]`)).toHaveClass(/\bon\b/)
  }

  // Still there after a reload, read from the server.
  await page.reload()
  await expect(folder.locator('li.doc')).toHaveCount(3)
  await expect(folder.locator('.chip.on')).toHaveCount(3)

  // Tidy the shared store: the papers, then the folder.
  const docs = (await (await page.request.get(`${API}/documents`)).json()).documents
  const folders = (await (await page.request.get(`${API}/folders`)).json()).folders
  const id = folders.find((f) => f.name === name).id
  const mine = docs.filter((d) => d.folder_id === id)
  expect(mine.map((d) => d.paper_part).sort()).toEqual(['booklet_a', 'booklet_b', 'paper_2'])
  for (const d of mine) await page.request.delete(`${API}/documents/${d.id}`)
  await page.request.delete(`${API}/folders/${id}`)
})
