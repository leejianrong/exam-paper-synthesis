import { describe, it, expect, afterEach } from 'vitest'
import { Editor, type JSONContent } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { NodeSelection } from '@tiptap/pm/state'
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
})
