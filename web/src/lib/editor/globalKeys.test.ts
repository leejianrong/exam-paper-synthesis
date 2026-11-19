import { describe, it, expect } from 'vitest'
import { ariaKeys, globalShortcut, keyLabel, type Command } from './shortcuts'
import { filterCommands } from './CommandPalette.svelte'

const ev = (init: KeyboardEventInit) => new KeyboardEvent('keydown', init)

describe('globalShortcut (EXA-163)', () => {
  it('maps each chord to its command on a PC', () => {
    expect(globalShortcut(ev({ key: 'k', ctrlKey: true }), false, false)).toBe('palette')
    expect(globalShortcut(ev({ key: 'K', ctrlKey: true }), false, false)).toBe('palette')
    expect(globalShortcut(ev({ key: 'Enter', ctrlKey: true }), false, false)).toBe('addQuestion')
    expect(globalShortcut(ev({ key: 'k', code: 'KeyK', ctrlKey: true, altKey: true }), false, false)).toBe('answerKey')
    expect(globalShortcut(ev({ key: 'p', ctrlKey: true }), false, false)).toBe('preview')
    expect(globalShortcut(ev({ key: '\\', ctrlKey: true }), false, false)).toBe('panel')
    expect(globalShortcut(ev({ key: '/', ctrlKey: true }), false, false)).toBe('sheet')
    expect(globalShortcut(ev({ key: 'm', ctrlKey: true }), false, false)).toBe('equation')
  })

  it('takes Cmd, not Ctrl, on a Mac, and reads ⌥ by its physical key', () => {
    expect(globalShortcut(ev({ key: 'k', metaKey: true }), false, true)).toBe('palette')
    expect(globalShortcut(ev({ key: 'k', ctrlKey: true }), false, true)).toBeNull()
    expect(globalShortcut(ev({ key: '˚', code: 'KeyK', metaKey: true, altKey: true }), false, true)).toBe('answerKey')
    expect(globalShortcut(ev({ key: 'k', metaKey: true }), false, false)).toBeNull()
  })

  it('leaves typing keys and the browser essentials alone', () => {
    for (const key of ['b', 'i', 'u', 'z', 'y', 'r', 'l', 't', 'w', 'c', 'v', 'a', 's']) {
      expect(globalShortcut(ev({ key, ctrlKey: true }), false, false)).toBeNull()
    }
    expect(globalShortcut(ev({ key: 'k' }), false, false)).toBeNull()
    expect(globalShortcut(ev({ key: 'P', ctrlKey: true, shiftKey: true }), false, false)).toBeNull()
  })

  it('never inserts from a form field, though the others still work there', () => {
    expect(globalShortcut(ev({ key: 'Enter', ctrlKey: true }), true, false)).toBeNull()
    expect(globalShortcut(ev({ key: 'm', ctrlKey: true }), true, false)).toBeNull()
    expect(globalShortcut(ev({ key: 'k', ctrlKey: true }), true, false)).toBe('palette')
  })
})

describe('key labels', () => {
  it('reads the PC way on a PC and with Mac glyphs on a Mac', () => {
    expect(keyLabel('Ctrl+Alt+K', false)).toBe('Ctrl+Alt+K')
    expect(keyLabel('Ctrl+Alt+K', true)).toBe('⌥⌘K')
    expect(keyLabel('Ctrl+Enter', true)).toBe('⌘↩')
    expect(keyLabel('Alt+↑', true)).toBe('⌥↑')
    expect(keyLabel('R', true)).toBe('R')
  })

  it('names keys for aria-keyshortcuts', () => {
    expect(ariaKeys('Ctrl+Alt+K', false)).toBe('Control+Alt+K')
    expect(ariaKeys('Ctrl+K', true)).toBe('Meta+K')
    expect(ariaKeys('Alt+↓', false)).toBe('Alt+ArrowDown')
    expect(ariaKeys('Del', false)).toBe('Delete')
  })
})

describe('filterCommands', () => {
  const run = () => {}
  const cmds: Command[] = [
    { label: 'Page break', group: 'Insert', run },
    { label: 'Preview pages', group: 'View', run },
    { label: 'Make harder', group: 'Question 2', run },
    { label: 'Section', group: 'Insert', run },
  ]

  it('keeps every command for an empty query', () => {
    expect(filterCommands(cmds, '  ')).toEqual(cmds)
  })

  it('matches every word, labels before menu names', () => {
    expect(filterCommands(cmds, 'page').map((c) => c.label)).toEqual(['Page break', 'Preview pages'])
    expect(filterCommands(cmds, 'insert').map((c) => c.label)).toEqual(['Page break', 'Section'])
    expect(filterCommands(cmds, 'HARD q2').map((c) => c.label)).toEqual([])
    expect(filterCommands(cmds, 'harder question').map((c) => c.label)).toEqual(['Make harder'])
  })
})
