import { test, expect } from '@playwright/test'
import fs from 'node:fs'
import { API } from './ports.js'

/**
 * Browser acceptance for EXA-168: a folder holding a generated exam set downloads one answer-key
 * PDF for the whole set from its ⋯ menu; with a paper of the set gone, the item is disabled and
 * says what is missing. The store is shared with the other specs, so the folder name is unique.
 */

test('a generated exam set downloads one answer key from its folder menu', async ({ page }) => {
  const name = `E2E set key ${Date.now()}`
  const folder = await (await page.request.post(`${API}/folders`, { data: { name } })).json()
  const papers = []
  for (const template of ['p2', 'p1_booklet_b', 'p1_booklet_a']) {
    const made = await page.request.post(`${API}/documents/generate`, {
      data: { template, level: 'P6', seed: 11, folder_id: folder.id },
    })
    expect(made.ok()).toBeTruthy()
    papers.push(await made.json())
  }

  await page.goto('/')
  const region = page.getByRole('region', { name, exact: true })
  await expect(region.locator('li.row')).toHaveCount(3)
  await region.getByRole('button', { name: `Actions for folder “${name}”` }).click()
  const item = page.getByRole('menuitem', { name: /Download the set’s answer key/ })
  await expect(item).not.toHaveAttribute('aria-disabled', 'true')
  const [download] = await Promise.all([page.waitForEvent('download'), item.click()])
  expect(download.suggestedFilename()).toBe(`${name} answer key.pdf`)
  const pdf = fs.readFileSync(await download.path())
  expect(pdf.subarray(0, 5).toString()).toBe('%PDF-')
  expect(pdf.length).toBeGreaterThan(10_000)
  await expect(page.getByRole('status').filter({ hasText: 'Downloaded the answer key' })).toHaveCount(1)
  await expect(page.getByRole('alert')).toHaveCount(0)

  // The preview is the PDF's markup: the three booklet headings, in exam order.
  const html = await (await page.request.get(`${API}/folders/${folder.id}/key/preview`)).text()
  const heads = [...html.matchAll(/<h2 class="key-paper">([^<]*)<\/h2>/g)].map((m) => m[1])
  expect(heads).toEqual(['Paper 1 Booklet A', 'Paper 1 Booklet B', 'Paper 2'])

  // Without Booklet B the item stays in the menu, disabled, saying why.
  const bookletB = papers.find((p) => p.paper_part === 'booklet_b')
  await page.request.delete(`${API}/documents/${bookletB.id}`)
  await page.reload()
  await region.getByRole('button', { name: `Actions for folder “${name}”` }).click()
  const off = page.getByRole('menuitem', { name: /Download the set’s answer key/ })
  await expect(off).toHaveAttribute('aria-disabled', 'true')
  await expect(off).toContainText('This folder has no Booklet B.')
  await page.keyboard.press('Escape')

  for (const p of papers) await page.request.delete(`${API}/documents/${p.id}`)
  await page.request.delete(`${API}/folders/${folder.id}`)
})
