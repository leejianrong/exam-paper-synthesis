import { test, expect } from '@playwright/test'
import { generateSinglePaper } from './helpers.js'

/**
 * EXA-160: the editor header fits the laptops teachers use. At 1366 (a common school laptop) and
 * 1024 the page never scrolls sideways, and Preview and Export stay on screen.
 */
for (const width of [1366, 1024]) {
  test(`the editor header fits at ${width} px with Preview and Export on screen`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 })
    await page.goto('/')
    await generateSinglePaper(page, 'Paper 2', 'P6')
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
    // Export is one menu with the three PDFs.
    await page.getByRole('button', { name: 'Export', exact: true }).click()
    await expect(page.getByRole('menuitem')).toHaveText([
      'Student paper (PDF)',
      'Answer key (PDF)',
      'Paper and key together (PDF)',
    ])
    await page.keyboard.press('Escape')
    await expect(page.getByRole('button', { name: 'Export', exact: true })).toBeFocused()
  })
}
