import { describe, it, expect, afterEach } from 'vitest'
import { Editor, Node } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { NodeSelection } from '@tiptap/pm/state'
import { applyServerContent } from './paperOps'
import { BlankPage, CoverPage, coverNode } from './pages'
import type { DocJSON } from './doc'

// Stand-ins with the real names and the one attribute applyServerContent matches on.
const Templated = Node.create({ name: 'templatedQuestion', group: 'block', atom: true, addAttributes: () => ({ block_id: { default: null } }), parseHTML: () => [{ tag: 'div[data-t]' }], renderHTML: () => ['div', { 'data-t': '' }] })
const Freeform = Node.create({ name: 'freeformQuestion', group: 'block', content: 'paragraph+', addAttributes: () => ({ block_id: { default: null } }), parseHTML: () => [{ tag: 'div[data-f]' }], renderHTML: () => ['div', { 'data-f': '' }, 0] })

let editor: Editor | null = null
afterEach(() => {
  editor?.destroy()
  editor = null
})

describe('after a swap the caret is in the changed block (EXA-129)', () => {
  it("'Write my own' leaves the caret in the new placeholder, so typing never hits the cover", () => {
    const sent = {
      type: 'doc',
      content: [coverNode({ school: 'Pandan' }), { type: 'templatedQuestion', attrs: { block_id: 'q1' } }, { type: 'templatedQuestion', attrs: { block_id: 'q2' } }],
    } as unknown as DocJSON
    editor = new Editor({ extensions: [StarterKit, CoverPage, BlankPage, Templated, Freeform], content: sent })
    // The swap button's click selected the cover (the stale selection that caused the bug).
    editor.view.dispatch(editor.state.tr.setSelection(NodeSelection.create(editor.state.doc, 0)))
    const next = {
      type: 'doc',
      content: [sent.content![0], { type: 'freeformQuestion', attrs: { block_id: 'q1' }, content: [{ type: 'paragraph' }] }, sent.content![2]],
    } as unknown as DocJSON
    expect(applyServerContent(editor, sent, next)).toBe(1)
    const $from = editor.state.selection.$from
    expect(editor.state.selection instanceof NodeSelection).toBe(false)
    expect($from.node(1).type.name).toBe('freeformQuestion')
    editor.commands.insertContent('My own question.')
    const json = editor.getJSON().content ?? []
    expect(json[0]).toMatchObject({ type: 'coverPage', attrs: { school: 'Pandan' } })
    expect(JSON.stringify(json[1])).toContain('My own question.')
  })
})
