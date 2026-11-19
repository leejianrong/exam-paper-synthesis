import { describe, it, expect, vi } from 'vitest'
import { createRawSnippet } from 'svelte'
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte'
import Menu, { type MenuItem } from './Menu.svelte'

const text = (t: string) => createRawSnippet(() => ({ render: () => `<span>${t}</span>` }))

function setup(extra: Partial<MenuItem>[] = [], props: Record<string, unknown> = {}) {
  const calls: string[] = []
  const base: MenuItem[] = [
    { label: 'Student paper', onSelect: () => calls.push('student') },
    { label: 'Answer key', onSelect: () => calls.push('key'), shortcut: 'Ctrl+K' },
    { label: 'Paper and key', onSelect: () => calls.push('full'), separator: true },
  ]
  const items = [...base, ...extra.map((e, i) => ({ label: `Extra ${i}`, onSelect: () => calls.push(`extra${i}`), ...e }))]
  render(Menu, { props: { items, trigger: text('Export'), ...props } })
  const button = screen.getByRole('button', { name: 'Export' })
  return { calls, button }
}

const items = () => screen.getAllByRole('menuitem')

describe('Menu (menu button pattern)', () => {
  it('starts closed and says it has a menu', () => {
    const { button } = setup()
    expect(button).toHaveAttribute('aria-haspopup', 'menu')
    expect(button).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('menu')).toBeNull()
  })

  it('a click opens it with focus on the first item; a second click closes it', async () => {
    const { button } = setup()
    await fireEvent.click(button)
    expect(button).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('menu')).toHaveAttribute('id', button.getAttribute('aria-controls'))
    await waitFor(() => expect(items()[0]).toHaveFocus())
    await fireEvent.click(button)
    expect(screen.queryByRole('menu')).toBeNull()
  })

  it('ArrowDown opens on the first item, ArrowUp on the last', async () => {
    const { button } = setup()
    await fireEvent.keyDown(button, { key: 'ArrowUp' })
    await waitFor(() => expect(items()[2]).toHaveFocus())
    await fireEvent.keyDown(screen.getByRole('menu'), { key: 'Escape' })
    await fireEvent.keyDown(button, { key: 'ArrowDown' })
    await waitFor(() => expect(items()[0]).toHaveFocus())
  })

  it('arrows move and wrap, Home and End jump, a letter jumps to the next match', async () => {
    const { button } = setup([{ label: 'Another' }])
    await fireEvent.click(button)
    const menu = screen.getByRole('menu')
    await waitFor(() => expect(items()[0]).toHaveFocus())
    await fireEvent.keyDown(menu, { key: 'ArrowDown' })
    expect(items()[1]).toHaveFocus()
    await fireEvent.keyDown(menu, { key: 'ArrowUp' })
    await fireEvent.keyDown(menu, { key: 'ArrowUp' })
    expect(items()[3]).toHaveFocus() // wrapped to the last
    await fireEvent.keyDown(menu, { key: 'ArrowDown' })
    expect(items()[0]).toHaveFocus() // and back round
    await fireEvent.keyDown(menu, { key: 'End' })
    expect(items()[3]).toHaveFocus()
    await fireEvent.keyDown(menu, { key: 'Home' })
    expect(items()[0]).toHaveFocus()
    await fireEvent.keyDown(menu, { key: 'a' })
    expect(items()[1]).toHaveFocus() // "Answer key"
    await fireEvent.keyDown(menu, { key: 'a' })
    expect(items()[3]).toHaveFocus() // the next "A…": "Another"
  })

  it('Escape closes and returns focus to the trigger without choosing', async () => {
    const { button, calls } = setup()
    await fireEvent.click(button)
    await fireEvent.keyDown(screen.getByRole('menu'), { key: 'Escape' })
    expect(screen.queryByRole('menu')).toBeNull()
    expect(button).toHaveFocus()
    expect(button).toHaveAttribute('aria-expanded', 'false')
    expect(calls).toEqual([])
  })

  it('choosing an item runs it once, closes and refocuses the trigger', async () => {
    const { button, calls } = setup()
    await fireEvent.click(button)
    await fireEvent.click(screen.getByRole('menuitem', { name: /Answer key/ }))
    expect(calls).toEqual(['key'])
    expect(screen.queryByRole('menu')).toBeNull()
    expect(button).toHaveFocus()
  })

  it('a disabled item stays reachable but does nothing, and says why', async () => {
    const onSelect = vi.fn()
    const { button } = setup([{ label: 'Equation', disabled: true, hint: 'Put the cursor in text first', onSelect }])
    await fireEvent.click(button)
    const eq = screen.getByRole('menuitem', { name: 'Equation' })
    expect(eq).toHaveAttribute('aria-disabled', 'true')
    expect(eq).toHaveAttribute('title', 'Put the cursor in text first')
    await fireEvent.click(eq)
    expect(onSelect).not.toHaveBeenCalled()
    expect(screen.getByRole('menu')).toBeInTheDocument()
  })

  it('a pointer press outside closes it; Tab closes it too', async () => {
    const { button } = setup()
    await fireEvent.click(button)
    await fireEvent.pointerDown(document.body)
    expect(screen.queryByRole('menu')).toBeNull()
    await fireEvent.click(button)
    await fireEvent.keyDown(screen.getByRole('menu'), { key: 'Tab' })
    expect(screen.queryByRole('menu')).toBeNull()
  })

  it('draws group separators, shortcuts, and a footer that is not an item', async () => {
    const { button } = setup([], { footer: text('24 exports left today') })
    await fireEvent.click(button)
    expect(screen.getAllByRole('separator')).toHaveLength(1)
    expect(screen.getByRole('menuitem', { name: /Answer key/ })).toHaveTextContent('Ctrl+K')
    expect(screen.getByText('24 exports left today')).toBeInTheDocument()
    expect(items()).toHaveLength(3)
  })

  it('takes an accessible name for an icon-only trigger', () => {
    render(Menu, { props: { items: [], trigger: text('⋯'), label: 'More tools' } })
    expect(screen.getByRole('button', { name: 'More tools' })).toBeInTheDocument()
  })
})
