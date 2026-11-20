import { describe, it, expect, afterEach } from 'vitest'
import { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { NodeSelection, TextSelection } from '@tiptap/pm/state'
import { FreeformQuestion, QuestionDocument } from './freeformQuestion'
import { ImageBlock, MathNode } from './media'
import { Section } from './sections'
import { GroupStem, groupStep, insertStem, stemMembers, stemSentence, setStemCount } from './groupStem'
import { moveBlock } from './templatedQuestion'
import { buildDocument, type DocJSON } from './doc'

const para = (t?: string) => ({ type: 'paragraph', content: t ? [{ type: 'text', text: t }] : undefined })
const q = (id: string) => ({
  type: 'freeformQuestion',
  attrs: { block_id: id, marks: 2, answer: { type: 'doc', content: [] } },
  content: [para(id)],
})
const stem = (count: number, text = 'The table shows the cost of postage.') => ({
  type: 'groupStem',
  attrs: { block_id: 'gs_test_1', count },
  content: [para(text)],
})

let editor: Editor
function make(doc: object[]) {
  editor = new Editor({
    element: document.body.appendChild(document.createElement('div')),
    extensions: [
      QuestionDocument,
      ImageBlock,
      MathNode,
      FreeformQuestion,
      Section,
      GroupStem,
      StarterKit.configure({ document: false, trailingNode: false, codeBlock: false }),
    ],
    content: { type: 'doc', content: doc } as never,
  })
  return editor
}
afterEach(() => editor?.destroy())
const json = () => editor.getJSON() as DocJSON
const count = () => json().content.find((n) => n.type === 'groupStem')?.attrs?.count
/** The top-level offset of the block with this id. */
function posOf(id: string): number {
  let at = -1
  editor.state.doc.forEach((c, p) => {
    if (c.attrs.block_id === id) at = p
  })
  return at
}
const tick = () => new Promise((r) => setTimeout(r, 0))

describe('membership and the lead line (engine mirror)', () => {
  it('takes the next count questions, with rich text between, and stops at a section or stem', () => {
    const blocks = [
      { type: 'groupStem', attrs: { count: 3 } },
      { type: 'freeformQuestion' },
      { type: 'paragraph' },
      { type: 'templatedQuestion' },
      { type: 'section' },
      { type: 'freeformQuestion' },
    ]
    expect(stemMembers(blocks, 0)).toEqual([1, 3])
  })
  it('words the lead line from the numbers', () => {
    expect(stemSentence([12, 13])).toBe('Use the information below to answer Questions 12 and 13.')
    expect(stemSentence([3, 4, 5])).toBe('Use the information below to answer Questions 3 to 5.')
    expect(stemSentence([7])).toBe('Use the information below to answer Question 7.')
    expect(stemSentence([])).toBe('')
  })
})

describe('the stem on the page', () => {
  it('shows the derived lead line and marks its questions', async () => {
    make([q('ffa1'), stem(2), q('ffb1'), q('ffc1'), q('ffd1')])
    await tick()
    expect(document.querySelector('.group-lead')?.textContent).toBe(
      'Use the information below to answer Questions 2 and 3.',
    )
    expect(document.querySelectorAll('.in-group')).toHaveLength(2)
    expect(document.querySelector('.group-count')?.textContent).toBe('2 questions')
  })

  it('takes in the next question and lets the last one go with its buttons', async () => {
    make([stem(2), q('ffa1'), q('ffb1'), q('ffc1')])
    await tick()
    const more = document.querySelector('.group-more') as HTMLButtonElement
    const fewer = document.querySelector('.group-fewer') as HTMLButtonElement
    expect(more.getAttribute('aria-label')).toMatch(/next question/)
    more.click()
    expect(count()).toBe(3)
    await tick()
    expect(document.querySelector('.group-lead')?.textContent).toMatch(/Questions 1 to 3/)
    expect(more.disabled).toBe(true) // no question left to take in
    fewer.click()
    fewer.click()
    expect(count()).toBe(1)
    await tick()
    expect(fewer.disabled).toBe(true)
  })

  it('deletes the stem and keeps its questions', async () => {
    make([stem(2), q('ffa1'), q('ffb1')])
    await tick()
    ;(document.querySelector('.group-delete') as HTMLButtonElement).click()
    expect(json().content.map((n) => n.type)).toEqual(['freeformQuestion', 'freeformQuestion'])
  })

  it('says when no question follows it yet', async () => {
    make([q('ffa1'), stem(2)])
    await tick()
    expect(document.querySelector('.group-lead')?.classList.contains('empty')).toBe(true)
  })
})

describe('keeping its questions through edits', () => {
  it('a deleted question leaves the group without pulling the next one in', () => {
    make([stem(2), q('ffa1'), q('ffb1'), q('ffc1')])
    const at = posOf('ffb1')
    editor.view.dispatch(editor.state.tr.delete(at, at + editor.state.doc.nodeAt(at)!.nodeSize))
    expect(count()).toBe(1)
  })

  it('a question inserted between two of its questions joins it', () => {
    make([stem(2), q('ffa1'), q('ffb1'), q('ffc1')])
    const at = posOf('ffb1')
    editor.view.dispatch(editor.state.tr.insert(at, editor.schema.nodeFromJSON(q('ffnew'))))
    expect(count()).toBe(3)
  })

  it('a question added after its last one does not join it', () => {
    make([stem(2), q('ffa1'), q('ffb1')])
    editor.view.dispatch(editor.state.tr.insert(editor.state.doc.content.size, editor.schema.nodeFromJSON(q('ffnew'))))
    expect(count()).toBe(2)
  })

  it('undo brings the count back with the question', () => {
    make([stem(2), q('ffa1'), q('ffb1'), q('ffc1')])
    const at = posOf('ffa1')
    editor.view.dispatch(editor.state.tr.delete(at, at + editor.state.doc.nodeAt(at)!.nodeSize))
    expect(count()).toBe(1)
    editor.commands.undo()
    expect(count()).toBe(2)
    expect(json().content).toHaveLength(4)
  })

  it('its own count change is left alone', () => {
    make([stem(1), q('ffa1'), q('ffb1')])
    editor.view.dispatch(setStemCount(editor.state, 0, 2)!)
    expect(count()).toBe(2)
  })
})

describe('moving questions in and out of a group', () => {
  it('down from the last place leaves the group; up from just under it joins', () => {
    make([stem(2), q('ffa1'), q('ffb1'), q('ffc1')])
    const size = (id: string) => editor.state.doc.nodeAt(posOf(id))!.nodeSize
    expect(groupStep(editor.state.doc, 2, 1)).not.toBeNull()
    moveBlock(editor, posOf('ffb1'), size('ffb1'), 1)
    expect(count()).toBe(1)
    expect(json().content.map((n) => n.attrs?.block_id)).toEqual(['gs_test_1', 'ffa1', 'ffb1', 'ffc1'])
    moveBlock(editor, posOf('ffb1'), size('ffb1'), -1)
    expect(count()).toBe(2)
    // inside the group a move is an ordinary swap and both stay in
    moveBlock(editor, posOf('ffb1'), size('ffb1'), -1)
    expect(json().content.map((n) => n.attrs?.block_id)).toEqual(['gs_test_1', 'ffb1', 'ffa1', 'ffc1'])
    expect(count()).toBe(2)
  })

  it('up past the stem leaves the group', () => {
    make([stem(2), q('ffa1'), q('ffb1'), q('ffc1')])
    moveBlock(editor, posOf('ffa1'), editor.state.doc.nodeAt(posOf('ffa1'))!.nodeSize, -1)
    expect(json().content.map((n) => n.attrs?.block_id)).toEqual(['ffa1', 'gs_test_1', 'ffb1', 'ffc1'])
    expect(count()).toBe(1)
  })
})

describe('inserting a stem', () => {
  it('goes before the question the caret is in, caret in the stem', () => {
    make([q('ffa1'), q('ffb1'), q('ffc1')])
    editor.view.dispatch(editor.state.tr.setSelection(TextSelection.create(editor.state.doc, posOf('ffb1') + 2)))
    insertStem(editor)
    expect(json().content.map((n) => n.type)).toEqual(['freeformQuestion', 'groupStem', 'freeformQuestion', 'freeformQuestion'])
    expect(editor.state.selection.$from.parent.type.name).toBe('paragraph')
    expect(editor.state.selection.$from.node(1).type.name).toBe('groupStem')
  })

  it('goes after a selected section', () => {
    make([{ type: 'section', attrs: { title: 'B' } }, q('ffa1'), q('ffb1')])
    editor.view.dispatch(editor.state.tr.setSelection(NodeSelection.create(editor.state.doc, 0)))
    insertStem(editor)
    expect(json().content.map((n) => n.type)).toEqual(['section', 'groupStem', 'freeformQuestion', 'freeformQuestion'])
  })
})

describe('saving', () => {
  it('stores only the id and count, with a fresh id for a pasted copy', () => {
    const doc = buildDocument('P', {
      type: 'doc',
      content: [
        { type: 'groupStem', attrs: { block_id: 'gs_same', count: 2, extra: 1 }, content: [para('x')] },
        { type: 'groupStem', attrs: { block_id: 'gs_same', count: 0 }, content: [para('y')] },
      ],
    })
    const [a, b] = doc.content.content
    expect(a.attrs).toEqual({ block_id: 'gs_same', count: 2 })
    expect(b.attrs?.block_id).not.toBe('gs_same')
    expect(b.attrs?.count).toBe(2)
    expect(doc.schema_version).toBe('1.17.0')
  })
})
