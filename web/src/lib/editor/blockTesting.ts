// Test helpers for a question block's controls (EXA-161): they show only when the block is
// selected, and most actions live in its ⋯ menu.
import { expect } from 'vitest'
import { fireEvent, waitFor, within } from '@testing-library/svelte'

/** The block's node view element (the focusable group). */
export function host(el: Element): HTMLElement {
  return (el.closest('.qblock') ?? el) as HTMLElement
}

/** Select the block (as a click or Tab would), so its pill shows. */
export async function selectBlock(el: Element): Promise<HTMLElement> {
  const h = host(el)
  await fireEvent.focusIn(h)
  await waitFor(() => expect(h.querySelector('.qpill')).not.toBeNull())
  return h
}

/** A button in the block's pill. */
export async function pillButton(el: Element, name: string | RegExp): Promise<HTMLElement> {
  const h = await selectBlock(el)
  return within(h.querySelector('.qpill') as HTMLElement).getByRole('button', { name })
}

/** Open the block's ⋯ menu and return it. */
export async function openMenu(el: Element): Promise<HTMLElement> {
  const h = await selectBlock(el)
  await fireEvent.click(within(h).getByRole('button', { name: /^More actions/ }))
  return within(h).findByRole('menu')
}

/** The labels of the block's menu rows, in order. */
export async function menuLabels(el: Element): Promise<string[]> {
  const menu = await openMenu(el)
  const labels = within(menu)
    .getAllByRole('menuitem')
    .map((r) => r.querySelector('.label')?.textContent ?? '')
  await fireEvent.keyDown(menu, { key: 'Escape' })
  return labels
}

/** Choose a row from the block's ⋯ menu. */
export async function chooseFromMenu(el: Element, name: string | RegExp): Promise<void> {
  const menu = await openMenu(el)
  await fireEvent.click(within(menu).getByRole('menuitem', { name }))
}
