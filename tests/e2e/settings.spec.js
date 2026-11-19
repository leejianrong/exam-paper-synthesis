import { test, expect } from '@playwright/test'
import { API } from './ports.js'
import { newBlankPaper } from './helpers.js'

/**
 * Browser acceptance for O1 (EXA-125): the Classic generator is hidden until a teacher turns it
 * on in Settings; the setting is saved on the account (it survives a reload).
 */
test('the Classic generator is hidden until it is turned on in Settings', async ({ page }) => {
  const off = await page.request.put(`${API}/settings`, { data: { classic_generator: false } })
  expect(off.ok()).toBeTruthy()

  await page.goto('/')
  const nav = page.getByRole('navigation', { name: 'Main' })
  await expect(nav.getByRole('link', { name: 'Papers' })).toBeVisible()
  await expect(nav.getByRole('link', { name: 'Classic' })).toHaveCount(0)

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

  // The Classic generator is a tab of the app header now, on every screen
  await nav.getByRole('link', { name: 'Classic' }).click()
  await expect(page.getByRole('button', { name: 'Generate', exact: true })).toBeVisible()
})

test('the answer key style in Settings is the key new papers start with', async ({ page }) => {
  // the e2e store is shared: start from the default and put it back after
  expect((await page.request.put(`${API}/settings`, { data: { answer_key_style: 'school' } })).ok()).toBeTruthy()
  try {
    await page.goto('/#/settings')
    const styles = page.getByRole('radiogroup', { name: 'Answer key style' })
    await expect(styles.getByRole('radio', { name: 'School key' })).toBeChecked()
    await styles.getByRole('radio', { name: 'Worked solutions' }).check()
    await expect(page.getByRole('status')).toHaveText('New papers get worked solutions.')
    await page.reload()
    await expect(styles.getByRole('radio', { name: 'Worked solutions' })).toBeChecked()

    await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Papers' }).click()
    await newBlankPaper(page)
    await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
    await page.getByRole('group', { name: 'View' }).getByRole('button', { name: 'Answer key' }).click()
    const style = page.getByRole('radiogroup', { name: 'Answer key style' })
    await expect(style.getByRole('radio', { name: 'Worked solutions' })).toBeChecked()
  } finally {
    await page.request.put(`${API}/settings`, { data: { answer_key_style: 'school' } })
  }
})

test('new-paper defaults: a school name and P5 in Settings fill an exam set’s covers', async ({ page }) => {
  // EXA-169. The e2e store is shared: start from the defaults and put them back after.
  test.setTimeout(120_000)
  const defaults = { school_name: '', default_level: '', marks_placement: 'answer' }
  expect((await page.request.put(`${API}/settings`, { data: defaults })).ok()).toBeTruthy()
  const shots = process.env.E2E_SHOTS_DIR // screenshots for review, when asked for
  const name = `E2E defaults ${Date.now()}`
  try {
    await page.goto('/#/settings')
    const group = page.getByRole('group', { name: 'New papers' })
    const school = group.getByRole('textbox', { name: 'School name' })
    await school.fill('Example Primary School')
    await school.press('Tab')
    await expect(page.getByRole('status')).toHaveText("New papers' covers will say Example Primary School.")
    await group.getByRole('radiogroup', { name: 'Level' }).getByRole('radio', { name: 'P5' }).check()
    await expect(page.getByRole('status')).toHaveText('New papers are P5.')
    await group.getByRole('combobox', { name: 'Marks shown' }).selectOption({ label: 'Both' })
    await expect(page.getByRole('status')).toHaveText('Marks shown on new papers: Both.')
    if (shots) await page.screenshot({ path: `${shots}/settings-new-papers.png`, fullPage: true })
    await page.reload()
    await expect(page.getByRole('textbox', { name: 'School name' })).toHaveValue('Example Primary School')

    await page.getByRole('navigation', { name: 'Main' }).getByRole('link', { name: 'Papers' }).click()
    await page.getByRole('button', { name: '+ New', exact: true }).click()
    const dialog = page.getByRole('dialog')
    await dialog.getByRole('button', { name: 'Exam set', exact: true }).click()
    await expect(dialog.getByRole('textbox', { name: 'Folder name' })).toHaveValue('P5 exam set')
    await dialog.getByRole('textbox', { name: 'Folder name' }).fill(name)
    await dialog.getByRole('button', { name: 'Next' }).click()
    const p5 = dialog.getByRole('button', { name: 'Generate at P5' })
    await expect(p5).toBeFocused() // preselected
    await expect(p5).toHaveAccessibleDescription('Your default')
    if (shots) await page.screenshot({ path: `${shots}/new-dialog-default-level.png` })
    await page.keyboard.press('Enter')
    await expect(dialog).toHaveCount(0, { timeout: 90_000 })

    const folder = page.getByRole('region', { name, exact: true })
    await expect(folder.locator('li.row')).toHaveCount(3)
    const folders = (await (await page.request.get(`${API}/folders`)).json()).folders
    const folderId = folders.find((f) => f.name === name).id
    const listed = (await (await page.request.get(`${API}/documents`)).json()).documents
    const mine = listed.filter((d) => d.folder_id === folderId)
    expect(mine).toHaveLength(3)
    for (const d of mine) {
      const doc = (await (await page.request.get(`${API}/documents/${d.id}`)).json()).document
      const cover = doc.content.content[0]
      expect(cover.type).toBe('coverPage')
      expect(cover.attrs.school).toBe('Example Primary School')
      expect(cover.attrs.level).toBe('Primary 5')
      expect(doc.title.startsWith('P5 ')).toBeTruthy()
      expect(doc.settings.marks_placement).toBe('both')
    }

    // The cover card in the editor says them too.
    await folder.locator('li.row').first().getByRole('link').click()
    const card = page.locator('.cover-block')
    await expect(card).toContainText('Example Primary School')
    await expect(card).toContainText('Primary 5')
    if (shots) await card.screenshot({ path: `${shots}/editor-cover-card.png` })

    for (const d of mine) await page.request.delete(`${API}/documents/${d.id}`)
    await page.request.delete(`${API}/folders/${folderId}`)
  } finally {
    await page.request.put(`${API}/settings`, { data: defaults })
  }
})
