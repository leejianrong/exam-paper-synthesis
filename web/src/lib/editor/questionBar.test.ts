// EXA-161: a question block's controls in the editor. Nothing at rest; selecting a block shows
// its pill; the ⋯ menu opens from the pill, a right-click or Shift+F10; the block shortcuts
// work on a focused or selected block and never while typing.
import { describe, it, expect, afterEach, vi } from 'vitest'
import { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { fireEvent, screen, waitFor, within } from '@testing-library/svelte'
import { TemplatedQuestion, moveBlock, questionNode } from './templatedQuestion'
import { FreeformQuestion, QuestionDocument } from './freeformQuestion'
import { BlockShortcuts, isBlockKeyTarget } from './shortcuts'
import { BlockSelectionGuard } from './blockSelection'
import { makeQuestion } from './fixtures'
import { ImageBlock, MathNode } from './media'
import { chooseFromMenu, menuLabels, openMenu, selectBlock } from './blockTesting'
import type { DocJSON } from './doc'
import { CoverPage, coverNode } from './pages'

let editor: Editor | null = null
afterEach(() => {
  editor?.destroy()
  editor = null
  document.body.innerHTML = ''
  vi.unstubAllGlobals()
})

const para = (t: string) => ({ type: 'paragraph', content: [{ type: 'text', text: t }] })
const placeholder = (id: string) => ({
  type: 'freeformQuestion',
  attrs: { block_id: id, marks: 2, answer: { type: 'doc', content: [] }, slot: { placeholder: true, marks: 2, kind: 'short' } },
  content: [{ type: 'paragraph' }],
})
const own = (id: string, text: string) => ({
  type: 'freeformQuestion',
  attrs: { block_id: id, marks: 1, answer: { type: 'doc', content: [] } },
  content: [para(text)],
})

function make(content: object[], { guard = false } = {}) {
  const onSwap = vi.fn(async () => {})
  const onDeleted = vi.fn()
  const onNotice = vi.fn()
  editor = new Editor({
    element: document.body.appendChild(document.createElement('div')),
    extensions: [
      QuestionDocument,
      ImageBlock,
      MathNode,
      StarterKit.configure({ document: false, trailingNode: false }),
      CoverPage,
      BlockShortcuts,
      ...(guard ? [BlockSelectionGuard] : []),
      TemplatedQuestion.configure({ onSwap, onDeleted, onNotice }),
      FreeformQuestion.configure({ onSwap, onDeleted }),
    ],
    content: { type: 'doc', content } as DocJSON as never,
  })
  return { editor, onSwap, onDeleted, onNotice }
}

const gq = (id: string, text: string) => {
  const n = questionNode(makeQuestion({ id }, text))
  return { ...n, attrs: { ...n.attrs, block_id: id } }
}
const ids = (e: Editor) => (e.getJSON().content ?? []).map((n) => n.attrs?.block_id)
const attrsOf = (e: Editor, id: string) => (e.getJSON().content ?? []).find((n) => n.attrs?.block_id === id)?.attrs ?? {}
const qblock = (text: string) => screen.getByText(text).closest('.qblock') as HTMLElement
const tick = () => new Promise((r) => setTimeout(r))

describe('at rest and selected', () => {
  it('shows no controls at rest; focusing a block shows its pill', async () => {
    make([gq('a', 'First.'), gq('b', 'Second.')])
    await tick()
    expect(document.querySelector('.qpill')).toBeNull()
    const a = qblock('First.')
    // a focusable, named group
    expect(a).toHaveAttribute('tabindex', '0')
    expect(a).toHaveAttribute('role', 'group')
    expect(a).toHaveAccessibleName('Question 1, 3 marks')
    a.focus()
    await waitFor(() => expect(a.querySelector('.qpill')).not.toBeNull())
    expect(a).toHaveClass('is-active')
    const pill = within(a.querySelector('.qpill') as HTMLElement)
    expect(pill.getAllByRole('button').map((b) => b.getAttribute('aria-label') ?? b.textContent?.trim())).toEqual([
      'Another like this',
      'Lock',
      'More actions for question 1',
    ])
    // only one block is selected at a time
    expect(qblock('Second.').querySelector('.qpill')).toBeNull()
  })

  it('a free-form question shows marks, + Part and ⋯; a placeholder, "Fill with a question" and ⋯', async () => {
    make([own('o1', 'My own words.'), placeholder('p1')])
    await tick()
    const mine = qblock('My own words.')
    expect(mine).toHaveAccessibleName('Question 1, 1 mark')
    await selectBlock(mine)
    const pill = within(mine.querySelector('.qpill') as HTMLElement)
    expect(pill.getByLabelText('Marks')).toHaveValue(1)
    expect(pill.getByRole('button', { name: 'Part' })).toBeInTheDocument()
    expect(pill.queryByRole('button', { name: 'Lock' })).toBeNull() // not the generator's
    expect(await menuLabels(mine)).toEqual(['Add a part', 'Edit answer…', 'Leave out of answer key', 'Move down', 'Add question below', 'Delete'])

    const slot = document.querySelectorAll<HTMLElement>('.ffblock')[1]
    expect(slot).toHaveClass('placeholder-slot')
    expect(slot).toHaveAccessibleName('Question 2, 2 marks, to write')
    await selectBlock(slot)
    const sp = within(slot.querySelector('.qpill') as HTMLElement)
    // a structured slot is written as parts: "+ Part" stays (as on main)
    expect(sp.getAllByRole('button').map((b) => b.getAttribute('aria-label') ?? b.textContent?.trim())).toEqual([
      'Fill with a question',
      'Part',
      'More actions for question 2',
    ])
    expect(await menuLabels(slot)).toContain('Add a part')
  })

  it('a right-click or Shift+F10 opens the same menu', async () => {
    make([gq('a', 'First.')])
    await tick()
    const a = qblock('First.')
    await fireEvent.contextMenu(a.querySelector('.num') as HTMLElement)
    const menu = await within(a).findByRole('menu')
    expect(within(menu).getByRole('menuitem', { name: 'Another like this' })).toHaveFocus()
    expect(within(menu).getByRole('menuitem', { name: 'Make easier' })).toHaveAttribute('aria-keyshortcuts', '[')
    await fireEvent.keyDown(menu, { key: 'Escape' })
    await waitFor(() => expect(within(a).queryByRole('menu')).toBeNull())

    a.focus()
    await fireEvent.keyDown(a, { key: 'F10', shiftKey: true })
    expect(await within(a).findByRole('menu')).toBeInTheDocument()
  })

  it('the ⋮⋮ handle opens the menu too, and says it is a menu button', async () => {
    make([gq('a', 'First.')])
    await tick()
    const a = qblock('First.')
    const handle = within(a).getByRole('button', { name: 'Menu for question 1' })
    expect(handle).toHaveAttribute('aria-haspopup', 'menu')
    expect(handle).toHaveAttribute('aria-expanded', 'false')
    await fireEvent.click(handle)
    expect(await within(a).findByRole('menu')).toBeInTheDocument()
    expect(handle).toHaveAttribute('aria-expanded', 'true')
  })

  it('a right-click over selected text or a figure keeps the browser menu', async () => {
    make([gq('a', 'First.')])
    await tick()
    const a = qblock('First.')
    const text = within(a).getByText('First.')
    const range = document.createRange()
    range.selectNodeContents(text)
    document.getSelection()?.removeAllRanges()
    document.getSelection()?.addRange(range)
    const rightClick = (el: Element) => {
      const ev = new MouseEvent('contextmenu', { bubbles: true, cancelable: true })
      el.dispatchEvent(ev)
      return !ev.defaultPrevented // true: the browser's own menu
    }
    expect(rightClick(text)).toBe(true)
    document.getSelection()?.removeAllRanges()
    const fig = a.appendChild(document.createElementNS('http://www.w3.org/2000/svg', 'svg'))
    expect(rightClick(fig)).toBe(true)
    fig.remove()
    expect(within(a).queryByRole('menu')).toBeNull()
    // elsewhere (no selection) it is ours
    expect(rightClick(text)).toBe(false)
    expect(await within(a).findByRole('menu')).toBeInTheDocument()
  })
})

describe('block shortcuts', () => {
  it('R, L, [ and ] on a focused question', async () => {
    const child = makeQuestion({ id: 'a:v2' }, 'Easier text.')
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ question: child }) })
    vi.stubGlobal('fetch', fetchMock)
    const { editor: e, onSwap } = make([gq('a', 'First.')])
    await tick()
    const a = qblock('First.')
    a.focus()
    await fireEvent.keyDown(a, { key: 'r' })
    expect(onSwap).toHaveBeenCalledWith('a', 'like')

    await fireEvent.keyDown(a, { key: 'l' })
    await waitFor(() => expect(attrsOf(e, 'a').locked).toBe(true))
    // locked: R does nothing now (its row is hidden)
    onSwap.mockClear()
    await fireEvent.keyDown(qblock('First.'), { key: 'r' })
    expect(onSwap).not.toHaveBeenCalled()

    await fireEvent.keyDown(qblock('First.'), { key: '[' })
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/edit\/make-easier$/)
    await waitFor(() => expect(screen.getByText('Easier text.')).toBeInTheDocument())
  })

  it('Alt+↓ / Alt+↑ move the focused question and keep focus on it', async () => {
    const { editor: e } = make([gq('a', 'First.'), gq('b', 'Second.')])
    await tick()
    qblock('First.').focus()
    await fireEvent.keyDown(qblock('First.'), { key: 'ArrowDown', altKey: true })
    await waitFor(() => expect(ids(e)).toEqual(['b', 'a']))
    await waitFor(() => expect(document.activeElement).toBe(qblock('First.')))
    await fireEvent.keyDown(qblock('First.'), { key: 'ArrowUp', altKey: true })
    await waitFor(() => expect(ids(e)).toEqual(['a', 'b']))
  })

  it('Del deletes the focused question and tells the page (which offers Undo)', async () => {
    const { editor: e, onDeleted } = make([gq('a', 'First.'), gq('b', 'Second.')])
    await tick()
    qblock('First.').focus()
    await fireEvent.keyDown(qblock('First.'), { key: 'Delete' })
    await waitFor(() => expect(ids(e)).toEqual(['b']))
    expect(onDeleted).toHaveBeenCalledTimes(1)
  })

  it('work on a question selected in the editor (arrow keys, after a swap)', async () => {
    const { editor: e, onDeleted } = make([gq('a', 'First.'), gq('b', 'Second.')])
    await tick()
    e.commands.setNodeSelection(0)
    e.view.focus()
    await fireEvent.keyDown(e.view.dom, { key: 'l' })
    await waitFor(() => expect(attrsOf(e, 'a').locked).toBe(true))
    expect(e.getText()).not.toContain('l') // nothing typed
    await fireEvent.keyDown(e.view.dom, { key: 'Delete' })
    await waitFor(() => expect(ids(e)).toEqual(['b']))
    expect(onDeleted).toHaveBeenCalledTimes(1)
  })

  it('never fire while typing in a question’s text, or in a field', async () => {
    const { editor: e, onSwap } = make([placeholder('p1'), own('o1', 'Words.')])
    await tick()
    // the caret in the placeholder's (empty) body
    e.commands.setTextSelection(2)
    e.view.focus()
    for (const key of ['r', 'l', '[', ']']) await fireEvent.keyDown(e.view.dom, { key })
    expect(onSwap).not.toHaveBeenCalled()
    expect(attrsOf(e, 'p1').locked).toBe(false)
    expect(ids(e)).toEqual(['p1', 'o1'])
    // …but Alt+↓ (which types nothing) still moves it
    await fireEvent.keyDown(e.view.dom, { key: 'ArrowDown', altKey: true })
    await waitFor(() => expect(ids(e)).toEqual(['o1', 'p1']))

    // the marks field in the pill keeps its keys
    const mine = qblock('Words.')
    const marks = within(await selectBlock(mine)).getByLabelText('Marks')
    marks.focus()
    await fireEvent.keyDown(marks, { key: 'Delete' })
    expect(ids(e)).toEqual(['o1', 'p1'])
  })
})

describe('a key typed on a selected question (EXA-171)', () => {
  afterEach(() => vi.useRealTimers())

  it('types nothing, and the pill says once per selection how to write below it', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const { editor: e } = make([gq('a', 'First.'), gq('b', 'Second.')], { guard: true })
    await tick()
    const before = e.getJSON()
    const host = qblock('First.')
    const hint = () => within(host).queryByRole('status')
    e.commands.setNodeSelection(0)
    e.view.focus()
    await waitFor(() => expect(host.querySelector('.qpill')).not.toBeNull())
    // the live region is there, empty, from the moment the pill shows, so the text that
    // appears in it is announced
    const region = hint()
    expect(region).not.toBeNull()
    expect(region?.textContent).toBe('')
    await fireEvent.keyDown(e.view.dom, { key: 'a' })
    await waitFor(() => expect(hint()).toHaveTextContent('Press Enter to write below'))
    expect(hint()).toBe(region)
    expect(e.getJSON()).toEqual(before)
    // it goes after a few seconds, and does not come back for this selection
    vi.advanceTimersByTime(4000)
    await waitFor(() => expect(hint()?.textContent).toBe(''))
    await fireEvent.keyDown(e.view.dom, { key: 's' })
    await tick()
    expect(hint()?.textContent).toBe('')
    // a new selection may show it again; a block shortcut never does
    e.commands.setNodeSelection(e.state.doc.child(0).nodeSize)
    await tick()
    e.commands.setNodeSelection(0)
    await fireEvent.keyDown(e.view.dom, { key: 'l' })
    await waitFor(() => expect(attrsOf(e, 'a').locked).toBe(true))
    expect(hint()?.textContent).toBe('')
    await fireEvent.keyDown(e.view.dom, { key: '7' })
    await waitFor(() => expect(hint()).toHaveTextContent('Press Enter to write below'))
    expect((e.getJSON().content ?? []).map((n) => n.type)).toEqual(['templatedQuestion', 'templatedQuestion'])
  })
})

describe('[ and ] on layouts that need AltGr or ⌥ (EXA-172)', () => {
  const altGr = { ctrlKey: true, altKey: true, modifierAltGraph: true } as KeyboardEventInit
  function selected() {
    const child = makeQuestion({ id: 'a:v2' }, 'Changed text.')
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ question: child }) })
    vi.stubGlobal('fetch', fetchMock)
    const made = make([gq('a', 'First.'), gq('b', 'Second.')], { guard: true })
    made.editor.commands.setNodeSelection(0)
    made.editor.view.focus()
    const press = (key: string, init: KeyboardEventInit = {}) => {
      const ev = new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true, ...init })
      made.editor.view.dom.dispatchEvent(ev)
      return ev
    }
    return { ...made, fetchMock, press }
  }
  const edits = (f: ReturnType<typeof vi.fn>) => f.mock.calls.map((c) => String(c[0]).split('/').pop())

  it('AltGr+[ on a German Windows keyboard makes the selected question easier', async () => {
    const { fetchMock, press } = selected()
    await tick()
    expect(press('[', altGr).defaultPrevented).toBe(true)
    await waitFor(() => expect(edits(fetchMock)).toEqual(['make-easier']))
  })

  it('AltGr+] makes it harder', async () => {
    const { fetchMock, press } = selected()
    await tick()
    expect(press(']', altGr).defaultPrevented).toBe(true)
    await waitFor(() => expect(edits(fetchMock)).toEqual(['make-harder']))
  })

  it('⌥[ on a German Mac makes it easier', async () => {
    const platform = vi.spyOn(navigator, 'platform', 'get').mockReturnValue('MacIntel')
    try {
      const { fetchMock, press } = selected()
      await tick()
      expect(press('[', { altKey: true }).defaultPrevented).toBe(true)
      await waitFor(() => expect(edits(fetchMock)).toEqual(['make-easier']))
    } finally {
      platform.mockRestore()
    }
  })

  it('Ctrl+[ and Cmd+[ are not the shortcut, and pass through untouched', async () => {
    const { editor: e, fetchMock, press } = selected()
    await tick()
    const before = e.getJSON()
    expect(press('[', { ctrlKey: true }).defaultPrevented).toBe(false)
    expect(press(']', { metaKey: true }).defaultPrevented).toBe(false)
    await tick()
    expect(fetchMock).not.toHaveBeenCalled()
    expect(e.getJSON()).toEqual(before)
    // …while the same key with AltGr is
    expect(press('[', altGr).defaultPrevented).toBe(true)
    await waitFor(() => expect(edits(fetchMock)).toEqual(['make-easier']))
  })

  it('the keypad - types nothing and sends no edit; the main-row - makes it easier', async () => {
    const { editor: e, fetchMock, press } = selected()
    await tick()
    const before = e.getJSON()
    expect(press('-', { code: 'NumpadSubtract' }).defaultPrevented).toBe(true) // dropped by the guard
    await tick()
    expect(fetchMock).not.toHaveBeenCalled()
    expect(e.getJSON()).toEqual(before)
    press('-', { code: 'Minus' })
    await waitFor(() => expect(edits(fetchMock)).toEqual(['make-easier']))
  })

  it('another AltGr character on a selected question is still dropped, with the hint', async () => {
    const { editor: e, fetchMock, press } = selected()
    await tick()
    const before = e.getJSON()
    expect(press('@', { ...altGr, code: 'KeyQ' }).defaultPrevented).toBe(true) // German AltGr+Q
    expect(press('{', { ...altGr, code: 'Digit7' }).defaultPrevented).toBe(true)
    await waitFor(() => expect(within(qblock('First.')).getByRole('status')).toHaveTextContent('Press Enter to write below'))
    expect(fetchMock).not.toHaveBeenCalled()
    expect(e.getJSON()).toEqual(before)
    // only [ and ] (and - =) of the AltGr characters are shortcuts
    press(']', altGr)
    await waitFor(() => expect(edits(fetchMock)).toEqual(['make-harder']))
  })

  it('with the caret in text an AltGr [ is left to the editor to type', async () => {
    const child = makeQuestion({ id: 'a:v2' }, 'Changed text.')
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ question: child }) })
    vi.stubGlobal('fetch', fetchMock)
    const { editor: e, onSwap } = make([own('o1', 'Words.'), gq('a', 'First.')], { guard: true })
    await tick()
    e.commands.setTextSelection(3)
    e.view.focus()
    const press = () => {
      const ev = new KeyboardEvent('keydown', { key: '[', bubbles: true, cancelable: true, ...altGr })
      e.view.dom.dispatchEvent(ev)
      return ev
    }
    expect(press().defaultPrevented).toBe(false)
    await tick()
    expect(fetchMock).not.toHaveBeenCalled()
    expect(onSwap).not.toHaveBeenCalled()
    expect(e.state.selection.from).toBe(3)
    // the generated question after it, selected, takes the same key
    e.commands.setNodeSelection(e.state.doc.child(0).nodeSize)
    expect(press().defaultPrevented).toBe(true)
    await waitFor(() => expect(edits(fetchMock)).toEqual(['make-easier']))
  })
})

/** A fetch that answers only when told to (a slow /edit). */
function slowFetch() {
  let answer: (q: unknown) => void = () => {}
  const fetchMock = vi.fn(
    () =>
      new Promise((resolve) => {
        answer = (question) => resolve({ ok: true, status: 200, json: async () => ({ question }) })
      }),
  )
  vi.stubGlobal('fetch', fetchMock)
  return { fetchMock, answer: (q: unknown) => answer(q) }
}
const questionId = (e: Editor, id: string) => (attrsOf(e, id).question as { id: string } | undefined)?.id

describe('a reply that arrives late (review)', () => {
  it('Make harder, then the question is deleted: the reply touches nothing else', async () => {
    const { answer } = slowFetch()
    const { editor: e, onNotice } = make([coverNode({ school: 'Example Primary' }), gq('a', 'First.'), gq('b', 'Second.')])
    await tick()
    const before = JSON.stringify(e.getJSON().content?.slice(0, 2))
    qblock('Second.').focus()
    await fireEvent.keyDown(qblock('Second.'), { key: ']' })
    // deleted before the reply (here as a selection deleted in the editor: its own menu waits)
    let at = -1
    e.state.doc.forEach((n, off) => {
      if (n.attrs.block_id === 'b') at = off
    })
    e.commands.deleteRange({ from: at, to: at + (e.state.doc.nodeAt(at)?.nodeSize ?? 0) })
    expect(ids(e)).toEqual([undefined, 'a'])
    answer(makeQuestion({ id: 'b:v2' }, 'Harder text.'))
    await waitFor(() => expect(onNotice).toHaveBeenCalledWith('That question was removed before the change arrived.'))
    expect(JSON.stringify(e.getJSON().content)).toBe(before) // the cover and Q1 untouched
    expect(screen.queryByText('Harder text.')).toBeNull()
  })

  it('Make harder, then the question moves: the reply lands on it in its new place', async () => {
    const { answer } = slowFetch()
    const { editor: e, onNotice } = make([gq('a', 'First.'), gq('b', 'Second.')])
    await tick()
    qblock('Second.').focus()
    await fireEvent.keyDown(qblock('Second.'), { key: ']' })
    moveBlock(e, e.state.doc.child(0).nodeSize, e.state.doc.child(1).nodeSize, -1)
    expect(ids(e)).toEqual(['b', 'a'])
    answer(makeQuestion({ id: 'b:v2' }, 'Harder text.'))
    await waitFor(() => expect(questionId(e, 'b')).toBe('b:v2'))
    expect(questionId(e, 'a')).toBe('a')
    expect(onNotice).not.toHaveBeenCalled()
  })
})

describe('a reply after the block got another question (re-review)', () => {
  it('Make harder, then Regenerate unlocked refills the block: the reply is dropped', async () => {
    const { answer } = slowFetch()
    const { editor: e, onNotice } = make([gq('a', 'First.'), gq('b', 'Second.')])
    await tick()
    qblock('Second.').focus()
    await fireEvent.keyDown(qblock('Second.'), { key: ']' })
    // the server refilled block b (same block_id, a new question), as paper_swap does
    let at = -1
    e.state.doc.forEach((n, off) => {
      if (n.attrs.block_id === 'b') at = off
    })
    const live = e.state.doc.nodeAt(at)!
    e.view.dispatch(
      e.state.tr.setNodeMarkup(at, undefined, {
        ...live.attrs,
        question: makeQuestion({ id: 'regen:1' }, 'Regenerated text.'),
      }),
    )
    answer(makeQuestion({ id: 'b:v2' }, 'Harder text.'))
    await waitFor(() =>
      expect(onNotice).toHaveBeenCalledWith('That question changed before the edit arrived, so the edit was dropped.'),
    )
    expect(questionId(e, 'b')).toBe('regen:1')
    expect(screen.queryByText('Harder text.')).toBeNull()
  })
})

describe('while a block is busy (review)', () => {
  it('Delete on the block selected in the editor waits too (re-review)', async () => {
    slowFetch()
    const { editor: e, onDeleted } = make([gq('a', 'First.'), gq('b', 'Second.')])
    await tick()
    qblock('First.').focus()
    await fireEvent.keyDown(qblock('First.'), { key: '[' })
    e.commands.setNodeSelection(0)
    e.view.focus()
    await fireEvent.keyDown(e.view.dom, { key: 'Delete' })
    await fireEvent.keyDown(e.view.dom, { key: 'Backspace' })
    await tick()
    expect(ids(e)).toEqual(['a', 'b'])
    expect(onDeleted).not.toHaveBeenCalled()
  })

  it('every menu row is disabled, Delete included, and the shortcuts wait', async () => {
    const { answer } = slowFetch()
    const { editor: e, onSwap, onDeleted } = make([gq('a', 'First.'), gq('b', 'Second.')])
    await tick()
    const a = qblock('First.')
    a.focus()
    await fireEvent.keyDown(a, { key: '[' })
    const menu = await openMenu(a)
    const rows = within(menu).getAllByRole('menuitem')
    expect(rows.length).toBeGreaterThan(3)
    for (const row of rows) expect(row).toHaveAttribute('aria-disabled', 'true')
    await fireEvent.click(within(menu).getByRole('menuitem', { name: /Delete/ }))
    expect(ids(e)).toEqual(['a', 'b'])
    await fireEvent.keyDown(menu, { key: 'Escape' })
    for (const key of ['Delete', 'r', 'l']) await fireEvent.keyDown(qblock('First.'), { key })
    await fireEvent.keyDown(qblock('First.'), { key: 'ArrowDown', altKey: true })
    expect(ids(e)).toEqual(['a', 'b'])
    expect(onSwap).not.toHaveBeenCalled()
    expect(onDeleted).not.toHaveBeenCalled()
    expect(attrsOf(e, 'a').locked).toBeFalsy()
    answer(makeQuestion({ id: 'a:v2' }, 'Easier text.'))
    await waitFor(() => expect(screen.getByText('Easier text.')).toBeInTheDocument())
  })
})

describe('keys on other controls inside a block are theirs (review)', () => {
  it('the working-space grip: Backspace, R and Alt+↑ never delete, swap or move the question', async () => {
    const { editor: e, onSwap, onDeleted } = make([gq('a', 'First.'), gq('b', 'Second.')])
    await tick()
    const grip = within(qblock('Second.')).getByRole('slider', { name: 'Working space height' })
    grip.focus()
    await fireEvent.keyDown(grip, { key: 'Backspace' })
    await fireEvent.keyDown(grip, { key: 'r' })
    await fireEvent.keyDown(grip, { key: 'ArrowUp', altKey: true })
    await tick()
    expect(ids(e)).toEqual(['a', 'b'])
    expect(onSwap).not.toHaveBeenCalled()
    expect(onDeleted).not.toHaveBeenCalled()
  })

  it('a part\'s "Delete part" button: Delete and Alt+↑ are not the question\'s', async () => {
    const withParts = {
      ...own('o1', 'Stem.'),
      attrs: { ...own('o1', 'Stem.').attrs, marks: null },
      content: [
        para('Stem.'),
        { type: 'freeformPart', attrs: { marks: 1 }, content: [para('Part one.')] },
        { type: 'freeformPart', attrs: { marks: 2 }, content: [para('Part two.')] },
      ],
    }
    const { editor: e, onDeleted } = make([gq('a', 'First.'), withParts])
    await tick()
    e.commands.setTextSelection(e.state.doc.child(0).nodeSize + 2) // the caret in the stem
    const del = qblock('Stem.').querySelector<HTMLButtonElement>('.ffpart button.danger') as HTMLButtonElement
    del.focus()
    await fireEvent.keyDown(del, { key: 'Delete' })
    await fireEvent.keyDown(del, { key: 'ArrowUp', altKey: true })
    await tick()
    expect(ids(e)).toEqual(['a', 'o1'])
    expect(onDeleted).not.toHaveBeenCalled()
    expect(e.getJSON().content?.[1].content?.filter((c) => c.type === 'freeformPart')).toHaveLength(2)
  })

  it('a free-form question\'s grip: Alt+↑ is not the question\'s', async () => {
    const { editor: e } = make([gq('a', 'First.'), own('o1', 'Mine.')])
    await tick()
    e.commands.setTextSelection(e.state.doc.child(0).nodeSize + 2) // the caret in its text
    const grip = within(qblock('Mine.')).getByRole('slider', { name: 'Working space height' })
    grip.focus()
    await fireEvent.keyDown(grip, { key: 'ArrowUp', altKey: true })
    await fireEvent.keyDown(grip, { key: 'Delete' })
    await tick()
    expect(ids(e)).toEqual(['a', 'o1'])
  })

  it('the names form: its buttons and fields keep R and Delete', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ slots: [{ key: 'names', role: 'name', count: 3, max_length: 24 }] }),
      }),
    )
    const { editor: e, onSwap, onDeleted } = make([gq('a', 'First.')])
    await tick()
    await chooseFromMenu(qblock('First.'), 'Edit names…')
    const form = await screen.findByRole('form', { name: 'Edit names' })
    await within(form).findByLabelText('Name 1')
    for (const name of ['Apply', 'Cancel']) {
      const b = within(form).getByRole('button', { name })
      b.focus()
      await fireEvent.keyDown(b, { key: 'r' })
      await fireEvent.keyDown(b, { key: 'Delete' })
      await fireEvent.keyDown(b, { key: 'l' })
    }
    expect(ids(e)).toEqual(['a'])
    expect(onSwap).not.toHaveBeenCalled()
    expect(onDeleted).not.toHaveBeenCalled()
    expect(attrsOf(e, 'a').locked).toBeFalsy()
  })

  it('isBlockKeyTarget: the block, its handle and pill buttons only', () => {
    const host = document.createElement('div')
    host.innerHTML =
      '<button class="qhandle"></button><div class="qpill"><button id="p"></button></div>' +
      '<div role="slider" tabindex="0"></div><button id="x"></button><a href="#">l</a>' +
      '<div class="qpill"><button data-own-keys id="o"></button></div><select></select>'
    const $ = (sel: string) => host.querySelector(sel)
    expect(isBlockKeyTarget(host, host)).toBe(true)
    expect(isBlockKeyTarget($('.qhandle'), host)).toBe(true)
    expect(isBlockKeyTarget($('#p'), host)).toBe(true)
    for (const sel of ['[role=slider]', '#x', 'a', '#o', 'select']) expect(isBlockKeyTarget($(sel), host)).toBe(false)
    expect(isBlockKeyTarget(document.createElement('button'), host)).toBe(false) // not in the block
  })
})

describe('Swap from your bank… (EXA-33)', () => {
  it('asks the page for a bank swap of a generated question and of an empty placeholder', async () => {
    const { onSwap } = make([gq('a', 'First.'), placeholder('p')])
    await tick()
    await chooseFromMenu(qblock('First.'), /Swap from your bank/)
    expect(onSwap).toHaveBeenCalledWith('a', 'bank')
    const slot = document.querySelector('[data-block-id="p"]') as HTMLElement
    await chooseFromMenu(slot, /Swap from your bank/)
    await waitFor(() => expect(onSwap).toHaveBeenCalledWith('p', 'bank'))
  })
})
