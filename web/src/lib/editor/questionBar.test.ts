// EXA-161: a question block's controls in the editor. Nothing at rest; selecting a block shows
// its pill; the ⋯ menu opens from the pill, a right-click or Shift+F10; the block shortcuts
// work on a focused or selected block and never while typing.
import { describe, it, expect, afterEach, vi } from 'vitest'
import { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { fireEvent, screen, waitFor, within } from '@testing-library/svelte'
import { TemplatedQuestion, questionNode } from './templatedQuestion'
import { FreeformQuestion, QuestionDocument } from './freeformQuestion'
import { BlockShortcuts } from './shortcuts'
import { makeQuestion } from './fixtures'
import { ImageBlock, MathNode } from './media'
import { menuLabels, selectBlock } from './blockTesting'
import type { DocJSON } from './doc'

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

function make(content: object[]) {
  const onSwap = vi.fn(async () => {})
  const onDeleted = vi.fn()
  editor = new Editor({
    element: document.body.appendChild(document.createElement('div')),
    extensions: [
      QuestionDocument,
      ImageBlock,
      MathNode,
      StarterKit.configure({ document: false, trailingNode: false }),
      BlockShortcuts,
      TemplatedQuestion.configure({ onSwap, onDeleted }),
      FreeformQuestion.configure({ onSwap, onDeleted }),
    ],
    content: { type: 'doc', content } as DocJSON as never,
  })
  return { editor, onSwap, onDeleted }
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
    expect(await menuLabels(mine)).toEqual(['Add a part', 'Leave out of answer key', 'Move down', 'Add question below', 'Delete'])

    const slot = document.querySelectorAll<HTMLElement>('.ffblock')[1]
    expect(slot).toHaveClass('placeholder-slot')
    expect(slot).toHaveAccessibleName('Question 2, 2 marks, to write')
    await selectBlock(slot)
    const sp = within(slot.querySelector('.qpill') as HTMLElement)
    expect(sp.getAllByRole('button').map((b) => b.getAttribute('aria-label') ?? b.textContent?.trim())).toEqual([
      'Fill with a question',
      'More actions for question 2',
    ])
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

  it('the ⋮⋮ handle opens the menu too', async () => {
    make([gq('a', 'First.')])
    await tick()
    const a = qblock('First.')
    await fireEvent.click(within(a).getByRole('button', { name: 'Menu for question 1' }))
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
