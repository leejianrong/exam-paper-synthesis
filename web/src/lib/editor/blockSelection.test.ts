import { describe, it, expect, afterEach } from 'vitest'
import { Editor, type JSONContent } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { NodeSelection } from '@tiptap/pm/state'
import { Slice, Fragment } from '@tiptap/pm/model'
import { Node } from '@tiptap/core'
import { BlockSelectionGuard, insertBlockSafely } from './blockSelection'
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

  it('typing over a selected part is not redirected (the guard only acts at the top level)', () => {
    const e = makeNested()
    const partPos = e.state.doc.child(0).nodeSize + 1
    e.view.dispatch(e.state.tr.setSelection(NodeSelection.create(e.state.doc, partPos)))
    const handled = e.view.someProp('handleTextInput', (f) => f(e.view, partPos, partPos, 'x', () => e.state.tr))
    expect(handled).toBeFalsy()
    expect(types(e).filter((t) => t === 'question')).toHaveLength(1)
  })

  it('a toolbar insert with a part selected goes after the whole question', () => {
    const e = makeNested()
    const partPos = e.state.doc.child(0).nodeSize + 1
    e.view.dispatch(e.state.tr.setSelection(NodeSelection.create(e.state.doc, partPos)))
    insertBlockSafely(e, blankPageNode())
    expect(types(e)).toEqual(['coverPage', 'question', 'blankPage', 'paragraph'])
  })
})
