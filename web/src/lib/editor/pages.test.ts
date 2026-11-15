import { describe, it, expect, afterEach } from 'vitest'
import { Editor, type JSONContent } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { cleanNode } from './doc'
import { BLANK_TEXT, BlankPage, CoverPage, blankPageNode, coverNode, hasCover } from './pages'

let editor: Editor | null = null
afterEach(() => {
  editor?.destroy()
  editor = null
})

function make(content: JSONContent[]) {
  editor = new Editor({
    extensions: [StarterKit, CoverPage, BlankPage],
    content: { type: 'doc', content },
  })
  return editor
}

const para = (text: string) => ({ type: 'paragraph', content: [{ type: 'text', text }] })

describe('cover page (P7)', () => {
  it('can be added as the first block', () => {
    const e = make([para('Question one')])
    expect(hasCover(e.state.doc)).toBe(false)
    e.chain().insertContentAt(0, coverNode({ school: 'Pandan Primary' })).run()
    expect(hasCover(e.state.doc)).toBe(true)
    expect(e.getJSON().content?.[0]).toMatchObject({
      type: 'coverPage',
      attrs: { school: 'Pandan Primary', subject: 'Mathematics' },
    })
  })

  it('is never allowed anywhere but first', () => {
    const e = make([coverNode(), para('a'), para('b')])
    // inserting a second cover further down is refused
    e.chain().insertContentAt(e.state.doc.content.size, coverNode()).run()
    expect(e.getJSON().content?.filter((n) => n.type === 'coverPage')).toHaveLength(1)
    // and so is putting text in front of it
    e.chain().insertContentAt(0, para('before')).run()
    expect(e.getJSON().content?.[0]?.type).toBe('coverPage')
  })

  it('serialises only what is set', () => {
    expect(
      cleanNode({
        type: 'coverPage',
        attrs: {
          school: ' Pandan ',
          exam: '',
          level: null,
          subject: 'Mathematics',
          paper: 'Paper 1',
          date: '  ',
          instructions: 'Answer all.\n',
          examiner_table: null,
        },
      }).attrs,
    ).toEqual({ school: 'Pandan', subject: 'Mathematics', paper: 'Paper 1', instructions: 'Answer all.' })
    expect(cleanNode({ type: 'coverPage', attrs: { examiner_table: false } }).attrs).toEqual({
      examiner_table: false,
    })
  })
})

describe('blank page (P7)', () => {
  it('inserts anywhere and serialises its kind and only a real text', () => {
    const e = make([para('a'), blankPageNode('rough'), para('b')])
    const node = e.getJSON().content?.[1]
    expect(node?.type).toBe('blankPage')
    expect(cleanNode(node!).attrs).toEqual({ kind: 'rough' })
    expect(cleanNode(blankPageNode('blank', ' Turn over ')).attrs).toEqual({
      kind: 'blank',
      text: 'Turn over',
    })
    expect(cleanNode({ type: 'blankPage', attrs: { kind: 'bogus' } }).attrs).toEqual({ kind: 'blank' })
  })

  it('shows its default wording as the placeholder', () => {
    const e = make([blankPageNode('rough')])
    const input = e.view.dom.querySelector<HTMLInputElement>('.blank-text-input')
    expect(input?.placeholder).toBe(BLANK_TEXT.rough)
  })
})
