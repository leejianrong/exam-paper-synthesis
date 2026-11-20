import { test, expect } from '@playwright/test'
import { generateSinglePaper } from './helpers.js'

/**
 * EXA-160: the editor header fits the laptops teachers use. At 1366 (a common school laptop), 1024
 * and 768 (a tablet) the page never scrolls sideways, and Preview, Export and the "N
 * placeholders to write" link stay on screen. A P5 Paper 2 is generated because it has a
 * placeholder (P6 seeds fill every slot), so the link is there to check.
 */
for (const width of [1366, 1024, 768]) {
  test(`the editor header fits at ${width} px with Preview and Export on screen`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 })
    await page.goto('/')
    await generateSinglePaper(page, 'Paper 2', 'P5')
    await expect(page).toHaveURL(/#\/docs\/[0-9a-f-]+$/)
    await expect(page.getByTestId('question-block').first()).toBeVisible()

    const widths = await page.evaluate(() => ({
      scroll: document.documentElement.scrollWidth,
      inner: window.innerWidth,
    }))
    expect(widths.scroll).toBeLessThanOrEqual(widths.inner)

    for (const name of ['Preview', 'Export']) {
      const button = page.getByRole('button', { name, exact: true })
      await expect(button).toBeVisible()
      await expect(button).toBeInViewport({ ratio: 1 })
    }
    const toWrite = page.getByTestId('header-placeholders')
    await expect(toWrite).toBeVisible()
    await expect(toWrite).toBeInViewport({ ratio: 1 })
    await expect(toWrite).toHaveText(/^\d+( placeholders?)? to write$/)
    // Export is one menu: the three PDFs, then the paper and key as Word files.
    await page.getByRole('button', { name: 'Export', exact: true }).click()
    await expect(page.getByRole('menu', { name: 'Export' }).getByRole('menuitem')).toHaveText([
      'Student paper (PDF)',
      'Answer key (PDF)',
      'Paper and key together (PDF)',
      'Student paper (Word)',
      'Answer key (Word)',
    ])
    await page.keyboard.press('Escape')
    await expect(page.getByRole('button', { name: 'Export', exact: true })).toBeFocused()
  })
}
