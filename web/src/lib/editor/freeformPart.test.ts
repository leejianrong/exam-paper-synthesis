import { describe, it, expect, afterEach } from 'vitest'
import { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { FreeformQuestion, QuestionDocument } from './freeformQuestion'
import { MAX_PARTS } from './freeformPart'
import { ImageBlock, MathNode } from './media'
import { buildDocument, cleanNode, type DocJSON } from './doc'
import { pillButton } from './blockTesting'

const para = (t?: string) => ({ type: 'paragraph', content: t ? [{ type: 'text', text: t }] : undefined })
const answer = (t: string) => ({ type: 'doc', content: [para(t)] })
const part = (t: string, attrs: object = {}) => ({
  type: 'freeformPart',
  attrs: { marks: 2, answer: answer('A'), ...attrs },
  content: [para(t)],
})
const question = (attrs: object, ...content: object[]) => ({
  type: 'freeformQuestion',
  attrs: { block_id: 'ff_test_1', marks: null, answer: { type: 'doc', content: [] }, ...attrs },
  content: [para('Stem.'), ...content],
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
      StarterKit.configure({ document: false, trailingNode: false, codeBlock: false }),
    ],
    content: { type: 'doc', content: doc } as never,
  })
  return editor
}
afterEach(() => editor?.destroy())
const json = () => editor.getJSON() as DocJSON
const click = (sel: string, i = 0) =>
  (document.querySelectorAll(sel)[i] as HTMLElement).click()
/** The pill's "+ Part" (EXA-161: the block's controls show once it is selected). */
const addPart = async () => (await pillButton(document.querySelector('.ffblock') as HTMLElement, 'Part')).click()

describe('part attributes survive copy and paste', () => {
  it('round-trips marks, answer, space and unit through HTML', () => {
    make([
      question(
        { marks: null },
        part('first', { marks: 3, answer: answer('30 l'), space_mm: 90, ans_unit: 'l' }),
      ),
    ])
    const html = editor.getHTML()
    editor.destroy()
    make([])
    editor.commands.setContent(html)
    const p = json().content[0].content?.find((c) => c.type === 'freeformPart')
    expect(p?.attrs).toMatchObject({ marks: 3, space_mm: 90, ans_unit: 'l' })
    expect(p?.attrs?.answer).toEqual(answer('30 l'))
    // and what it saves is a valid shape (numbers stay numbers, the answer stays an object)
    const saved = buildDocument('T', json()).content.content[0].content?.[1]
    expect(typeof saved?.attrs?.marks).toBe('number')
    expect(typeof saved?.attrs?.answer).toBe('object')
  })

  it('keeps a question-level space and unit as numbers and strings', () => {
    make([question({ marks: 2, space_mm: 60, ans_unit: 'cm' })])
    const html = editor.getHTML()
    editor.destroy()
    make([])
    editor.commands.setContent(html)
    expect(json().content[0].attrs).toMatchObject({ space_mm: 60, ans_unit: 'cm', marks: 2 })
  })
})

describe('adding and deleting parts loses nothing', () => {
  it('the first part takes the question marks and answer; the question gives them up', async () => {
    make([question({ marks: 5, answer: answer('OLD') })])
    await new Promise((r) => setTimeout(r))
    await addPart()
    const q = json().content[0]
    expect(q.attrs).toMatchObject({ marks: null })
    const p = q.content?.find((c) => c.type === 'freeformPart')
    expect(p?.attrs?.marks).toBe(5)
    expect(p?.attrs?.answer).toEqual(answer('OLD'))
  })

  it('puts the caret in the new part at once, so typing never reaches the button', async () => {
    make([question({ marks: 2 })])
    await new Promise((r) => setTimeout(r))
    await addPart()
    // synchronously, not a frame later: a key typed in between went to the button (a space
    // pressed it again and added a stray part)
    expect(editor.view.hasFocus()).toBe(true)
    const { $from } = editor.state.selection
    expect($from.node($from.depth - 1).type.name).toBe('freeformPart')
  })

  it('deleting the last part gives its marks and answer back to the question', async () => {
    make([question({ marks: null }, part('only', { marks: 4, answer: answer('MINE') }))])
    await new Promise((r) => setTimeout(r))
    click('.ffpart button.danger')
    const q = json().content[0]
    expect(q.content?.some((c) => c.type === 'freeformPart')).toBe(false)
    expect(q.attrs).toMatchObject({ marks: 4 })
    expect(q.attrs?.answer).toEqual(answer('MINE'))
  })

  it('deleting one of several parts leaves the question multi-part', async () => {
    make([question({ marks: null }, part('a'), part('b'))])
    await new Promise((r) => setTimeout(r))
    click('.ffpart button.danger')
    const q = json().content[0]
    expect(q.content?.filter((c) => c.type === 'freeformPart')).toHaveLength(1)
    expect(q.attrs?.marks).toBeNull()
  })
})

describe('the part cap', () => {
  it('refuses a paste that would exceed the limit the server enforces', () => {
    make([question({ marks: null }, ...Array.from({ length: MAX_PARTS }, (_, i) => part(`p${i}`)))])
    const html = editor.getHTML()
    editor.destroy()
    make([])
    editor.commands.setContent(html)
    const extra = editor.schema.nodeFromJSON(part('one too many'))
    const q = editor.state.doc.firstChild!
    editor.view.dispatch(editor.state.tr.insert(q.nodeSize - 1, extra)) // end of the question
    const parts = json().content[0].content?.filter((c) => c.type === 'freeformPart') ?? []
    expect(parts).toHaveLength(MAX_PARTS)
  })
})

describe('generated placeholders (P8a)', () => {
  const slot = { marks: 3, kind: 'structured', placeholder: true }
  const empty = () => ({
    type: 'freeformQuestion',
    attrs: { block_id: 'ff_ph_1', marks: 3, answer: { type: 'doc', content: [] }, slot },
    content: [{ type: 'paragraph' }],
  })

  it('keeps the slot through the editor and says what to write until the body has text', async () => {
    make([empty()])
    await new Promise((r) => setTimeout(r))
    expect(json().content[0].attrs?.slot).toEqual(slot)
    expect(cleanNode(json().content[0]).attrs?.slot).toEqual(slot)
    const hint = document.querySelector('.ff-placeholder-hint') as HTMLElement
    expect(hint.hidden).toBe(false)
    expect(hint.textContent).toBe('Placeholder: write a 3-mark structured question here, or delete it and add one.')
    editor.chain().setTextSelection(2).insertContent('A tank holds water.').run()
    await new Promise((r) => setTimeout(r))
    expect((document.querySelector('.ff-placeholder-hint') as HTMLElement).hidden).toBe(true)
  })

  it('an ordinary question stores no slot', () => {
    make([question({ marks: 2 })])
    expect(cleanNode(json().content[0]).attrs).not.toHaveProperty('slot')
  })
})
