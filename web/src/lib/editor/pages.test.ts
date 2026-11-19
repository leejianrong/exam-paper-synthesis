import { describe, it, expect, afterEach } from 'vitest'
import { Editor, type JSONContent } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { cleanNode } from './doc'
import {
  BLANK_TEXT,
  BlankPage,
  CoverPage,
  blankPageNode,
  coverNode,
  coverLines,
  coverPlacementOk,

  hasCover,
} from './pages'

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
    e.chain().insertContentAt(0, coverNode({ school: 'Example Primary' })).run()
    expect(hasCover(e.state.doc)).toBe(true)
    expect(e.getJSON().content?.[0]).toMatchObject({
      type: 'coverPage',
      attrs: { school: 'Example Primary', subject: 'Mathematics' },
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

  it('counts a cover nested inside a list as misplaced', () => {
    const e = make([para('a')])
    const nested = e.schema.nodeFromJSON({
      type: 'doc',
      content: [
        coverNode(),
        {
          type: 'bulletList',
          content: [{ type: 'listItem', content: [para('x'), coverNode()] }],
        },
      ],
    })
    expect(coverPlacementOk(nested)).toBe(false)
    expect(coverPlacementOk(e.schema.nodeFromJSON({ type: 'doc', content: [coverNode(), para('b')] }))).toBe(true)
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

describe('cover switches (EXA-140)', () => {
  it('serialises the parent signature and even-page switches only when set', () => {
    expect(
      cleanNode({ type: 'coverPage', attrs: { parent_signature: true, even_pages: false } }).attrs,
    ).toEqual({ parent_signature: true, even_pages: false })
    expect(
      cleanNode({ type: 'coverPage', attrs: { parent_signature: null, even_pages: null } }).attrs,
    ).toEqual({})
  })

})

describe('cover card (EXA-164)', () => {
  it('leads with school and exam, then level · subject · paper, leaving out empty ones', () => {
    expect(coverLines({ school: ' Example Primary ', exam: 'Prelim 2026', level: 'Primary 6', subject: 'Mathematics', paper: 'Paper 2' })).toEqual([
      'Example Primary',
      'Prelim 2026',
      'Primary 6 · Mathematics · Paper 2',
    ])
    expect(coverLines({ school: '', exam: null, level: '', subject: 'Mathematics', paper: '' })).toEqual(['Mathematics'])
    expect(coverLines({})).toEqual([])
  })

  it('is a compact card with no form; Edit and Alt+Enter open its settings', () => {
    const element = document.createElement('div')
    document.body.append(element)
    const opened: number[] = []
    editor = new Editor({
      element,
      extensions: [StarterKit, CoverPage.configure({ onEdit: (pos) => opened.push(pos) }), BlankPage],
      content: { type: 'doc', content: [coverNode({ school: 'Example Primary', level: 'Primary 6' }), para('a')] },
    })
    const card = element.querySelector('.cover-block')!
    expect(card.querySelectorAll('input, textarea, select')).toHaveLength(0)
    expect(Array.from(card.querySelectorAll('.cover-line')).map((p) => p.textContent)).toEqual([
      'Example Primary',
      'Primary 6 · Mathematics',
    ])
    card.querySelector<HTMLButtonElement>('button[aria-label="Edit cover page"]')!.click()
    expect(opened).toEqual([0])

    // An attribute set elsewhere (the side panel) shows on the card.
    editor.view.dispatch(editor.state.tr.setNodeMarkup(0, undefined, { ...editor.state.doc.firstChild!.attrs, exam: 'Prelim' }))
    expect(card.querySelectorAll('.cover-line')[1].textContent).toBe('Prelim')

    editor.commands.setNodeSelection(0)
    editor.view.dom.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', altKey: true, bubbles: true }))
    expect(opened).toEqual([0, 0])
    element.remove()
  })

  it('an empty cover asks for the school and exam', () => {
    const element = document.createElement('div')
    document.body.append(element)
    editor = new Editor({ element, extensions: [StarterKit, CoverPage, BlankPage], content: { type: 'doc', content: [coverNode({ subject: '' })] } })
    expect(element.querySelector('.cover-line.empty')?.textContent).toBe('Add the school and exam')
    expect(element.querySelector('.block-edit')).toBeNull() // no editor callback, no Edit button
    element.remove()
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
