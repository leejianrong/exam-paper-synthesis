import { describe, it, expect } from 'vitest'
import { blockLabel, menuGroups, pillActions, primaryRow, rowForShortcut, type QuestionFacts } from './questionMenu'
import { blockShortcut, isTypingTarget } from './shortcuts'

const facts = (over: Partial<QuestionFacts> = {}): QuestionFacts => ({
  kind: 'generated',
  locked: false,
  lockable: true,
  inKey: true,
  ops: ['regenerate', 'make-easier', 'make-harder'],
  canEditNames: true,
  canAddPart: false,
  canMoveUp: true,
  canMoveDown: true,
  ...over,
})
const labels = (f: QuestionFacts) => menuGroups(f).map((g) => g.map((r) => r.label))

describe('the question menu (EXA-161)', () => {
  it('a generated question: change it, keep it, place it, take it over, remove it', () => {
    expect(labels(facts())).toEqual([
      ['Another like this', 'Another topic', 'Make easier', 'Make harder', 'Edit names…'],
      ['Lock', 'Leave out of answer key'],
      ['Move up', 'Move down', 'Add question below'],
      ['Replace with my own question', 'Edit as my own text…'],
      ['Delete'],
    ])
    // "Regenerate" is merged into "Another like this", which is the server's like-swap
    expect(menuGroups(facts())[0][0].action).toBe('like')
    expect(labels(facts()).flat()).not.toContain('Regenerate')
  })

  it('the engine-specific edits join the first group only when offered', () => {
    const f = facts({
      ops: ['make-harder', 'change-to-decimals', 'toggle-bar-view'],
      opLabels: { 'toggle-bar-view': 'Group segments' },
    })
    expect(labels(f)[0]).toEqual(['Another like this', 'Another topic', 'Make harder', 'Edit names…', 'Change to decimals', 'Group segments'])
  })

  it('hides what does not apply: swaps on a locked question, moves at the ends, harder on the top rung', () => {
    const locked = labels(facts({ locked: true, canMoveUp: false, ops: ['make-easier'] })).flat()
    expect(locked).not.toContain('Another like this')
    expect(locked).not.toContain('Another topic')
    expect(locked).not.toContain('Replace with my own question')
    expect(locked).not.toContain('Move up')
    expect(locked).not.toContain('Make harder')
    expect(locked).toContain('Unlock')
    expect(locked).toContain('Edit as my own text…')
  })

  it('a bank question keeps only the page verbs', () => {
    expect(labels(facts({ kind: 'bank', lockable: false, ops: [], canEditNames: false, inKey: false }))).toEqual([
      ['Include in answer key'],
      ['Move up', 'Move down', 'Add question below'],
      ['Edit as my own text…'],
      ['Delete'],
    ])
  })

  it("a teacher's own question adds parts; a placeholder fills from the generator", () => {
    const own = facts({ kind: 'own', lockable: false, ops: [], canEditNames: false, canAddPart: true })
    expect(labels(own)[0]).toEqual(['Add a part'])
    // its answer is written by the teacher, for the key (EXA-162)
    expect(labels(own)[1]).toEqual(['Edit answer…', 'Leave out of answer key'])
    expect(labels(own).flat()).not.toContain('Edit as my own text…')
    expect(pillActions(own)).toEqual(['addPart'])

    const slot = facts({ kind: 'placeholder', ops: [], canEditNames: false })
    expect(labels(slot)[0]).toEqual(['Fill with a question', 'Another topic'])
    expect(labels(slot)[1]).toEqual(['Lock', 'Leave out of answer key'])
    expect(pillActions(slot)).toEqual(['primary'])
    expect(primaryRow(slot)?.label).toBe('Fill with a question')
  })

  it('the pill: the main verb, Lock, then ⋯', () => {
    expect(pillActions(facts())).toEqual(['primary', 'lock'])
    expect(primaryRow(facts())?.label).toBe('Another like this')
    expect(pillActions(facts({ kind: 'bank', lockable: false, ops: [] }))).toEqual([])
    // a locked question still offers the lock (to unlock) but no swap
    expect(pillActions(facts({ locked: true }))).toEqual(['lock'])
  })

  it('a shortcut runs the row that shows it, and nothing when that row is hidden', () => {
    expect(rowForShortcut(facts(), 'R')?.action).toBe('like')
    expect(rowForShortcut(facts(), '[')?.action).toBe('easier')
    expect(rowForShortcut(facts(), 'Del')?.action).toBe('delete')
    expect(rowForShortcut(facts({ locked: true }), 'R')).toBeUndefined()
    expect(rowForShortcut(facts({ canMoveDown: false }), 'Alt+↓')).toBeUndefined()
    expect(rowForShortcut(facts({ kind: 'placeholder' }), 'R')?.action).toBe('fill')
  })

  it("names the block: 'Question 6, 2 marks, locked'", () => {
    expect(blockLabel(6, 2, { locked: true, kind: 'generated' })).toBe('Question 6, 2 marks, locked')
    expect(blockLabel(1, 1, { locked: false, kind: 'own' })).toBe('Question 1, 1 mark')
    expect(blockLabel(3, 2, { locked: false, kind: 'placeholder' })).toBe('Question 3, 2 marks, to write')
  })
})

describe('block shortcuts', () => {
  const key = (key: string, mods: Partial<KeyboardEventInit> = {}) => new KeyboardEvent('keydown', { key, ...mods })

  it('maps keys to the labels the menu shows', () => {
    expect(blockShortcut(key('r'), false)).toBe('R')
    expect(blockShortcut(key('L'), false)).toBe('L')
    expect(blockShortcut(key('['), false)).toBe('[')
    expect(blockShortcut(key(']'), false)).toBe(']')
    expect(blockShortcut(key('ArrowUp', { altKey: true }), false)).toBe('Alt+↑')
    expect(blockShortcut(key('ArrowDown', { altKey: true }), false)).toBe('Alt+↓')
    expect(blockShortcut(key('Delete'), false)).toBe('Del')
    expect(blockShortcut(key('F10', { shiftKey: true }), false)).toBe('menu')
    expect(blockShortcut(key('ContextMenu'), false)).toBe('menu')
  })

  it('never takes a key that types, or a chord the browser or editor owns', () => {
    for (const k of ['r', 'l', '[', ']', 'Delete', 'Backspace']) expect(blockShortcut(key(k), true)).toBeNull()
    expect(blockShortcut(key('r', { ctrlKey: true }), false)).toBeNull()
    expect(blockShortcut(key('ArrowUp'), false)).toBeNull()
    // moving and the menu still work from inside text: they type nothing
    expect(blockShortcut(key('ArrowUp', { altKey: true }), true)).toBe('Alt+↑')
    expect(blockShortcut(key('F10', { shiftKey: true }), true)).toBe('menu')
  })

  // EXA-172: [ and ] need AltGr or ⌥ on many layouts; they are read by the character typed
  const altGr = (k: string, mods: Partial<KeyboardEventInit> = {}) =>
    key(k, { ctrlKey: true, altKey: true, modifierAltGraph: true, ...mods } as KeyboardEventInit)

  it('takes [ and ] typed with AltGr (German Windows: AltGr+8 / AltGr+9, reported as Ctrl+Alt)', () => {
    expect(blockShortcut(altGr('['), false, false)).toBe('[')
    expect(blockShortcut(altGr(']'), false, false)).toBe(']')
    // Linux reports AltGr alone, without Ctrl and Alt
    expect(blockShortcut(key('[', { modifierAltGraph: true } as KeyboardEventInit), false, false)).toBe('[')
    // Swiss and Hungarian-style layouts may add Shift; the character is still "["
    expect(blockShortcut(altGr(']', { shiftKey: true }), false, false)).toBe(']')
  })

  it("takes [ and ] typed with ⌥ on a Mac (German Mac: ⌥5 / ⌥6), and French Mac's ⌥⇧", () => {
    expect(blockShortcut(key('[', { altKey: true }), false, true)).toBe('[')
    expect(blockShortcut(key(']', { altKey: true }), false, true)).toBe(']')
    expect(blockShortcut(key('[', { altKey: true, shiftKey: true }), false, true)).toBe('[')
    // ⌥↑ still moves, and ⌥ with another character is not a shortcut
    expect(blockShortcut(key('ArrowUp', { altKey: true }), false, true)).toBe('Alt+↑')
    expect(blockShortcut(key('“', { altKey: true }), false, true)).toBeNull()
  })

  it('a real chord with [ or ] is not the shortcut: Ctrl+[, Cmd+[, Ctrl+Alt+[ without AltGr, Alt+[ off a Mac', () => {
    for (const mac of [false, true]) {
      expect(blockShortcut(key('[', { ctrlKey: true }), false, mac)).toBeNull()
      expect(blockShortcut(key(']', { metaKey: true }), false, mac)).toBeNull()
      expect(blockShortcut(key('[', { ctrlKey: true, altKey: true }), false, mac)).toBeNull()
      // Cmd with AltGr held is still a Cmd chord
      expect(blockShortcut(key('[', { metaKey: true, modifierAltGraph: true } as KeyboardEventInit), false, mac)).toBeNull()
    }
    expect(blockShortcut(key('[', { altKey: true }), false, false)).toBeNull()
    // …while the same key with AltGr is one
    expect(blockShortcut(altGr('['), false, false)).toBe('[')
  })

  it('- and = stand in for [ and ] (layouts without brackets), the same way', () => {
    expect(blockShortcut(key('-'), false, false)).toBe('[')
    expect(blockShortcut(key('='), false, false)).toBe(']')
    expect(blockShortcut(key('=', { shiftKey: true }), false, false)).toBe(']') // German Shift+0
    expect(blockShortcut(key('-', { ctrlKey: true }), false, false)).toBeNull() // zoom out
    expect(blockShortcut(key('=', { metaKey: true }), false, true)).toBeNull() // zoom in
  })

  it('- and = from the keypad type numbers, never a shortcut; the main-row keys are one', () => {
    expect(blockShortcut(key('-', { code: 'NumpadSubtract' }), false, false)).toBeNull()
    expect(blockShortcut(key('=', { code: 'NumpadEqual' }), false, true)).toBeNull()
    expect(blockShortcut(key('-', { code: 'Minus' }), false, false)).toBe('[')
    expect(blockShortcut(key('=', { code: 'Equal' }), false, true)).toBe(']')
  })

  it('nothing while an input method composes or opens (Process, keyCode 229)', () => {
    expect(blockShortcut(key('Process', { keyCode: 229 } as KeyboardEventInit), false, false)).toBeNull()
    expect(blockShortcut(key('[', { keyCode: 229 } as KeyboardEventInit), false, false)).toBeNull()
    expect(blockShortcut(key('r', { keyCode: 229 } as KeyboardEventInit), false, false)).toBeNull()
    expect(blockShortcut(key('[', { isComposing: true }), false, false)).toBeNull()
    expect(blockShortcut(key('[', { keyCode: 219 } as KeyboardEventInit), false, false)).toBe('[')
  })

  it('never in text, however the character is typed', () => {
    for (const k of ['[', ']', '-', '=']) {
      expect(blockShortcut(altGr(k), true, false)).toBeNull()
      expect(blockShortcut(key(k, { altKey: true }), true, true)).toBeNull()
      expect(blockShortcut(key(k), true, false)).toBeNull()
      expect(blockShortcut(altGr(k), false, false)).not.toBeNull() // on the block it is one
    }
  })

  it('AltGr with a letter is not R or L, even if the browser leaves e.key a letter', () => {
    expect(blockShortcut(altGr('r'), false, false)).toBeNull()
    expect(blockShortcut(altGr('l'), false, false)).toBeNull()
    expect(blockShortcut(altGr('@'), false, false)).toBeNull()
    expect(blockShortcut(altGr('['), false, false)).toBe('[')
  })

  it('knows where the author is typing', () => {
    const editable = document.createElement('div')
    editable.setAttribute('contenteditable', 'true')
    const text = document.createElement('p')
    const atom = document.createElement('div')
    atom.setAttribute('contenteditable', 'false')
    editable.append(text, atom)
    expect(isTypingTarget(text)).toBe(true)
    expect(isTypingTarget(atom)).toBe(false)
    expect(isTypingTarget(document.createElement('input'))).toBe(true)
    expect(isTypingTarget(document.createElement('button'))).toBe(false)
  })
})
