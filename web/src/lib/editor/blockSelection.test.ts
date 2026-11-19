import { describe, it, expect, afterEach, vi } from 'vitest'
import { Editor, type JSONContent } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { NodeSelection, TextSelection } from '@tiptap/pm/state'
import { Slice, Fragment } from '@tiptap/pm/model'
import { Node } from '@tiptap/core'
import { BlockSelectionGuard, insertBlockSafely } from './blockSelection'
import { BlockShortcuts, registerBlockKeys } from './shortcuts'
import { BlankPage, CoverPage, blankPageNode, coverNode } from './pages'

let editor: Editor | null = null
afterEach(() => {
  editor?.destroy()
  editor = null
})

function make(content: JSONContent[]) {
  editor = new Editor({
    extensions: [StarterKit, CoverPage, BlankPage, BlockSelectionGuard],
    content: { type: 'doc', content },
  })
  return editor
}
const para = (text: string) => ({ type: 'paragraph', content: [{ type: 'text', text }] })
const types = (e: Editor) => (e.getJSON().content ?? []).map((n) => n.type)
const selectCover = (e: Editor) => e.view.dispatch(e.state.tr.setSelection(NodeSelection.create(e.state.doc, 0)))

describe('a selected block is never replaced (EXA-129)', () => {
  it('a toolbar insert with the cover selected goes after the cover', () => {
    const e = make([coverNode(), para('Q1')])
    selectCover(e)
    insertBlockSafely(e, blankPageNode())
    expect(types(e)).toEqual(['coverPage', 'blankPage', 'paragraph'])
  })

  it('without a block selected, it inserts at the caret as before', () => {
    const e = make([coverNode(), para('Q1')])
    e.commands.setTextSelection(e.state.doc.content.size - 1)
    insertBlockSafely(e, blankPageNode())
    expect(types(e)).toContain('blankPage')
    expect(types(e)[0]).toBe('coverPage')
  })

  it('typing with the cover selected starts a paragraph after it', () => {
    const e = make([coverNode({ school: 'Pandan' }), para('Q1')])
    selectCover(e)
    const handled = e.view.someProp('handleTextInput', (f) => f(e.view, 0, 1, 'M', () => e.state.tr))
    expect(handled).toBe(true)
    const json = e.getJSON().content ?? []
    expect(json[0]).toMatchObject({ type: 'coverPage', attrs: { school: 'Pandan' } })
    expect(json[1]).toMatchObject({ type: 'paragraph', content: [{ type: 'text', text: 'M' }] })
    expect(e.state.selection.from).toBe(e.state.doc.child(0).nodeSize + 2) // caret after the M
  })

  it('Enter with the cover selected adds a paragraph after it', () => {
    const e = make([coverNode(), para('Q1')])
    selectCover(e)
    const ev = new KeyboardEvent('keydown', { key: 'Enter' })
    expect(e.view.someProp('handleKeyDown', (f) => f(e.view, ev))).toBe(true)
    expect(types(e)).toEqual(['coverPage', 'paragraph', 'paragraph'])
  })

  it('a paste with the cover selected lands after it', () => {
    const e = make([coverNode(), para('Q1')])
    selectCover(e)
    const slice = new Slice(Fragment.from(e.schema.nodes.paragraph.create(null, e.schema.text('Pasted'))), 0, 0)
    const handled = e.view.someProp('handlePaste', (f) => f(e.view, new Event('paste') as ClipboardEvent, slice))
    expect(handled).toBe(true)
    const json = e.getJSON().content ?? []
    expect(json[0].type).toBe('coverPage')
    expect(JSON.stringify(json)).toContain('Pasted')
  })
})

// A stand-in question with nested blocks, like a free-form question's lettered parts.
const Q = Node.create({ name: 'question', group: 'block', content: 'part+', parseHTML: () => [{ tag: 'div[data-q]' }], renderHTML: () => ['div', { 'data-q': '' }, 0] })
const Part = Node.create({ name: 'part', content: 'paragraph+', parseHTML: () => [{ tag: 'div[data-p]' }], renderHTML: () => ['div', { 'data-p': '' }, 0] })

describe('a block selected inside a question is left to the editor (no split question)', () => {
  function makeNested() {
    editor = new Editor({
      extensions: [StarterKit, CoverPage, BlankPage, BlockSelectionGuard, Q, Part],
      content: { type: 'doc', content: [coverNode(), { type: 'question', content: [{ type: 'part', content: [para('(a)')] }, { type: 'part', content: [para('(b)')] }] }, { type: 'paragraph' }] },
    })
    return editor
  }

  it('typing over a selected part does nothing: no split question, no part lost (EXA-171)', () => {
    const e = makeNested()
    const before = e.getJSON()
    const partPos = e.state.doc.child(0).nodeSize + 1
    e.view.dispatch(e.state.tr.setSelection(NodeSelection.create(e.state.doc, partPos)))
    const handled = e.view.someProp('handleTextInput', (f) => f(e.view, partPos, partPos, 'x', () => e.state.tr))
    expect(handled).toBe(true)
    expect(e.getJSON()).toEqual(before)
  })

  it('a toolbar insert with a part selected goes after the whole question', () => {
    const e = makeNested()
    const partPos = e.state.doc.child(0).nodeSize + 1
    e.view.dispatch(e.state.tr.setSelection(NodeSelection.create(e.state.doc, partPos)))
    insertBlockSafely(e, blankPageNode())
    expect(types(e)).toEqual(['coverPage', 'question', 'blankPage', 'paragraph'])
  })
})

// EXA-171: stand-ins named like the real question blocks (a generated question is an atom; a
// free-form question holds lettered parts).
const Templated = Node.create({ name: 'templatedQuestion', group: 'block', atom: true, parseHTML: () => [{ tag: 'div[data-tq]' }], renderHTML: () => ['div', { 'data-tq': '' }] })
const Freeform = Node.create({ name: 'freeformQuestion', group: 'block', content: 'freeformPart+', parseHTML: () => [{ tag: 'div[data-fq]' }], renderHTML: () => ['div', { 'data-fq': '' }, 0] })
const FreeformPart = Node.create({ name: 'freeformPart', content: 'paragraph+', parseHTML: () => [{ tag: 'div[data-fp]' }], renderHTML: () => ['div', { 'data-fp': '' }, 0] })

describe('typing on a selected question never replaces it (EXA-171)', () => {
  let onEdit: ReturnType<typeof vi.fn<(pos: number) => void>>
  function makeQ() {
    onEdit = vi.fn<(pos: number) => void>()
    editor = new Editor({
      extensions: [StarterKit, CoverPage.configure({ onEdit }), BlankPage, BlockSelectionGuard, BlockShortcuts, Templated, Freeform, FreeformPart],
      content: {
        type: 'doc',
        content: [
          coverNode({ school: 'Pandan' }),
          { type: 'templatedQuestion' },
          { type: 'freeformQuestion', content: [{ type: 'freeformPart', content: [para('(a)')] }, { type: 'freeformPart', content: [para('(b)')] }] },
          para('Last'),
        ],
      },
    })
    return editor
  }
  const posOf = (e: Editor, index: number) => {
    let pos = 0
    for (let i = 0; i < index; i++) pos += e.state.doc.child(i).nodeSize
    return pos
  }
  const select = (e: Editor, pos: number) => e.view.dispatch(e.state.tr.setSelection(NodeSelection.create(e.state.doc, pos)))
  const selectQuestion = (e: Editor) => select(e, posOf(e, 1))
  const selectPart = (e: Editor) => select(e, posOf(e, types(e).indexOf('freeformQuestion')) + 1)
  /** A key press as the browser delivers it: to the editor, cancelable. */
  const press = (e: Editor, key: string, init: KeyboardEventInit = {}) => {
    const ev = new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true, ...init })
    e.view.dom.dispatchEvent(ev)
    return ev
  }
  const input = (e: Editor, inputType: string, data: string | null) => {
    const ev = new InputEvent('beforeinput', { inputType, data, bubbles: true, cancelable: true })
    e.view.dom.dispatchEvent(ev)
    return ev
  }
  const stillSelected = (e: Editor, pos: number) => {
    expect(e.state.selection).toBeInstanceOf(NodeSelection)
    expect(e.state.selection.from).toBe(pos)
  }

  it('a letter does nothing on a selected question or part: the browser never types it', () => {
    const e = makeQ()
    const before = e.getJSON()
    selectQuestion(e)
    expect(press(e, 'a').defaultPrevented).toBe(true)
    expect(e.getJSON()).toEqual(before)
    stillSelected(e, posOf(e, 1))
    selectPart(e)
    expect(press(e, 'q').defaultPrevented).toBe(true)
    expect(press(e, 'Q', { shiftKey: true }).defaultPrevented).toBe(true)
    expect(e.getJSON()).toEqual(before)
  })

  it('a digit does nothing on a selected question', () => {
    const e = makeQ()
    const before = e.getJSON()
    selectQuestion(e)
    expect(press(e, '7').defaultPrevented).toBe(true)
    expect(e.getJSON()).toEqual(before)
    stillSelected(e, posOf(e, 1))
  })

  it('a space does nothing on a selected question', () => {
    const e = makeQ()
    const before = e.getJSON()
    selectQuestion(e)
    expect(press(e, ' ').defaultPrevented).toBe(true)
    expect(e.getJSON()).toEqual(before)
    stillSelected(e, posOf(e, 1))
  })

  it('on a selected cover a typed key starts a paragraph after it, on the key press itself', () => {
    const e = makeQ()
    select(e, 0)
    expect(press(e, '7').defaultPrevented).toBe(true)
    const json = e.getJSON().content ?? []
    expect(json[0]).toMatchObject({ type: 'coverPage', attrs: { school: 'Pandan' } })
    expect(json[1]).toMatchObject({ type: 'paragraph', content: [{ type: 'text', text: '7' }] })
    expect(json[2].type).toBe('templatedQuestion')
  })

  it("a mobile keyboard's insertText does nothing on a question and goes after a cover", () => {
    const e = makeQ()
    const before = e.getJSON()
    selectQuestion(e)
    expect(input(e, 'insertText', 'x').defaultPrevented).toBe(true)
    expect(input(e, 'insertReplacementText', 'word').defaultPrevented).toBe(true)
    expect(e.getJSON()).toEqual(before)
    expect(input(e, 'insertParagraph', null).defaultPrevented).toBe(true) // Enter: a paragraph after
    expect(types(e)).toEqual(['coverPage', 'templatedQuestion', 'paragraph', 'freeformQuestion', 'paragraph'])
    expect((e.getJSON().content ?? [])[2].content).toBeUndefined()
    selectPart(e)
    expect(input(e, 'insertText', 'x').defaultPrevented).toBe(true)
    expect((e.getJSON().content ?? [])[3]).toEqual((before.content ?? [])[2])
    select(e, 0)
    expect(input(e, 'insertText', 'M').defaultPrevented).toBe(true)
    expect((e.getJSON().content ?? [])[1]).toMatchObject({ type: 'paragraph', content: [{ type: 'text', text: 'M' }] })
  })

  it('an input method starts in a new paragraph after the question, never over it', () => {
    const e = makeQ()
    selectQuestion(e)
    const qEnd = posOf(e, 2)
    // the key that opens the IME ('Process'), then its composition
    expect(press(e, 'Process', { keyCode: 229 }).defaultPrevented).toBe(false)
    expect(types(e)).toEqual(['coverPage', 'templatedQuestion', 'paragraph', 'freeformQuestion', 'paragraph'])
    expect(e.state.selection).toBeInstanceOf(TextSelection)
    expect(e.state.selection.from).toBe(qEnd + 1)

    // compositionstart alone (no key press first) does the same, from a selected part too
    selectPart(e)
    e.view.dom.dispatchEvent(new CompositionEvent('compositionstart', { bubbles: true }))
    expect(e.state.selection).toBeInstanceOf(TextSelection)
    expect(e.state.selection.$from.parent.type.name).toBe('paragraph')
    expect(e.state.selection.$from.depth).toBe(1) // after the question, not inside a part
    expect(types(e).filter((t) => t === 'templatedQuestion' || t === 'freeformQuestion')).toHaveLength(2)
  })

  it('a paste over a selected question lands after it; over a selected part it is dropped', () => {
    const e = makeQ()
    const slice = () => new Slice(Fragment.from(e.schema.nodes.paragraph.create(null, e.schema.text('Pasted'))), 0, 0)
    const paste = () => e.view.someProp('handlePaste', (f) => f(e.view, new Event('paste') as ClipboardEvent, slice()))
    selectPart(e)
    const part = (e.getJSON().content ?? [])[2]
    expect(paste()).toBe(true)
    expect((e.getJSON().content ?? [])[2]).toEqual(part)
    expect(JSON.stringify(e.getJSON())).not.toContain('Pasted')
    expect(input(e, 'insertFromPaste', null).defaultPrevented).toBe(true)
    selectQuestion(e)
    expect(paste()).toBe(true)
    expect(types(e).slice(0, 3)).toEqual(['coverPage', 'templatedQuestion', 'paragraph'])
    expect(JSON.stringify((e.getJSON().content ?? [])[2])).toContain('Pasted')
  })

  it('only a selected block: with the caret in text, keys and input go to the editor as before', () => {
    const e = makeQ()
    selectQuestion(e)
    expect(press(e, 'a').defaultPrevented).toBe(true) // the selected question drops it
    const end = e.state.doc.content.size - 1
    e.commands.setTextSelection(end) // the caret at the end of "Last"
    const before = e.getJSON()
    expect(press(e, 'b').defaultPrevented).toBe(false)
    expect(press(e, ' ').defaultPrevented).toBe(false)
    expect(input(e, 'insertText', 'c').defaultPrevented).toBe(false)
    e.view.dom.dispatchEvent(new CompositionEvent('compositionstart', { bubbles: true }))
    expect(e.state.selection.from).toBe(end)
    expect(e.view.someProp('handleTextInput', (f) => f(e.view, end, end, 'd', () => e.state.tr))).toBeFalsy()
    expect(e.getJSON()).toEqual(before)
  })

  it('the block shortcuts, Enter, Alt+Enter and Delete still work on a selected block', () => {
    const e = makeQ()
    const qPos = posOf(e, 1)
    const handler = vi.fn((ev: KeyboardEvent) => ev.key === 'r')
    const unregister = registerBlockKeys(e.view.nodeDOM(qPos) as Element, handler)
    selectQuestion(e)
    expect(press(e, 'r').defaultPrevented).toBe(true)
    expect(handler).toHaveBeenCalledTimes(1)
    expect(press(e, 'a').defaultPrevented).toBe(true)
    expect(handler).toHaveBeenCalledTimes(2) // offered to the block first, then dropped
    unregister()
    // Alt+Enter on the cover opens its settings (EXA-164), with nothing added
    select(e, 0)
    press(e, 'Enter', { altKey: true })
    expect(onEdit).toHaveBeenCalledWith(0)
    expect(types(e)).toEqual(['coverPage', 'templatedQuestion', 'freeformQuestion', 'paragraph'])
    // Enter on a question starts a paragraph after it
    selectQuestion(e)
    expect(press(e, 'Enter').defaultPrevented).toBe(true)
    expect(types(e)).toEqual(['coverPage', 'templatedQuestion', 'paragraph', 'freeformQuestion', 'paragraph'])
    // Ctrl/Cmd chords are not text: Ctrl+A stays the editor's (select all)
    selectQuestion(e)
    press(e, 'a', { ctrlKey: true })
    expect(e.state.selection.from).toBe(0)
    expect(e.state.selection.to).toBe(e.state.doc.content.size)
    // Delete still deletes the selected question
    selectQuestion(e)
    press(e, 'Delete')
    expect(types(e)).not.toContain('templatedQuestion')
  })
})
