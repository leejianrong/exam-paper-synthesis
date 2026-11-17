// EXA-152: each question on the editing page shows its [n] as the paper prints it — by the
// effective marks placement of the section it sits in, live as sections change.
import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest'
import { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { waitFor } from '@testing-library/svelte'
import { FreeformQuestion, QuestionDocument } from './freeformQuestion'
import { TemplatedQuestion, questionNode } from './templatedQuestion'
import { ImageBlock, MathNode } from './media'
import { Section, blockPlacements, sectionNode } from './sections'
import { paperPlacement } from './layout'
import { paperSettings } from './paperSettings'
import { freeformDocNode, makeBankQuestion, makeMultipartQuestion, makeQuestion, routeFetch } from './fixtures'
import type { DocNode } from './doc'
import type { Question } from '../types'
import fixture from './placements.fixture.json'

describe('per-question placement equals the engine (placements.fixture.json)', () => {
  // The fixture is written by tests/test_editor_placement_fixture.py from engine.document.
  for (const row of fixture) {
    it(row.name, () => {
      const blocks = row.content.content as DocNode[]
      const all = blockPlacements(blocks, paperPlacement(row.settings))
      const questions = all.filter((_, i) =>
        ['templatedQuestion', 'freeformQuestion'].includes(blocks[i].type),
      )
      expect(questions).toEqual(row.expected)
    })
  }
})

// --- the node views -------------------------------------------------------------------------

const mcq = (): Question => {
  const q = makeQuestion({ id: 'mcq:1' }, 'Which is the largest?')
  q.question.parts[0].answer = { type: 'choice', options: [] } as never
  return q
}
const withParts = (): DocNode => ({
  type: 'freeformQuestion',
  attrs: { block_id: 'ff_parts', marks: null, answer: { type: 'doc', content: [] } },
  content: [
    { type: 'paragraph', content: [{ type: 'text', text: 'Stem.' }] },
    {
      type: 'freeformPart',
      attrs: { marks: 4, answer: { type: 'doc', content: [] } },
      content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Part one.' }] }],
    },
  ],
})
const block = (node: DocNode, id: string): DocNode => ({ ...node, attrs: { ...node.attrs, block_id: id } })

let editor: Editor
function make(content: DocNode[]) {
  editor = new Editor({
    element: document.body.appendChild(document.createElement('div')),
    extensions: [
      QuestionDocument,
      ImageBlock,
      MathNode,
      Section,
      FreeformQuestion,
      TemplatedQuestion,
      StarterKit.configure({ document: false, trailingNode: false, codeBlock: false }),
    ],
    content: { type: 'doc', content } as never,
  })
  return editor
}

beforeEach(() => {
  paperSettings.set({ marks_placement: 'answer' })
  // Engine-drawn questions (bank, multi-part) ask the server for the print markup, by placement.
  vi.stubGlobal(
    'fetch',
    routeFetch({
      '/render/question.css': '',
      '/render/katex.js': '',
      '/render/question': (init?: RequestInit) => {
        const body = JSON.parse(String(init?.body))
        return { html: `<div class="frag">placement=${body.placement}</div>` }
      },
    }),
  )
})
afterEach(() => {
  editor?.destroy()
  document.body.innerHTML = ''
  vi.unstubAllGlobals()
})

const el = (id: string) => document.querySelector(`[data-block-id="${id}"]`) as HTMLElement
const text = (root: Element, sel: string) =>
  [...root.querySelectorAll(sel)].map((n) => n.textContent?.trim() ?? '').filter(Boolean).join(' ')
/** What a block shows: [n] beside the question text, and [n] after its Ans: line(s). */
function shown(id: string): { beside: string; line: string } {
  const root = el(id)
  return {
    beside: text(root, '.meta .marks, .ff-marks, .ffp-marks'),
    line: text(root, '[data-testid="answer-area"] .marks'),
  }
}
const fragment = (id: string) =>
  el(id).querySelector('[data-testid="fragment"]')?.shadowRoot?.querySelector('.frag')?.textContent ?? ''

/** Set the section's attrs, as its "Marks shown" / "Mode" selects do. */
function setSection(attrs: Record<string, unknown>) {
  let at = -1
  editor.state.doc.forEach((n, offset) => {
    if (n.type.name === 'section' && at < 0) at = offset
  })
  const node = editor.state.doc.nodeAt(at)!
  editor.view.dispatch(editor.state.tr.setNodeMarkup(at, undefined, { ...node.attrs, ...attrs }))
}

function paper(): DocNode[] {
  return [
    block(freeformDocNode({ marks: 5 }), 'before'),
    sectionNode('Booklet B', { mode: 'structured' }),
    questionNode(makeQuestion()),
    questionNode(mcq()),
    block(freeformDocNode({ marks: 2 }), 'single'),
    withParts(),
    questionNode(makeBankQuestion()),
    questionNode(makeMultipartQuestion()),
  ]
}
const ids = () => {
  const out: string[] = []
  editor.state.doc.forEach((n) => {
    if (n.type.name !== 'section') out.push(String(n.attrs.block_id))
  })
  return out
}

describe('question node views show [n] by their section (EXA-152)', () => {
  it('follows the section, every kind of question block, and updates live', async () => {
    make(paper())
    const [before, templated, choice, single, parts, bank, multi] = ids()

    // A structured section with no choice follows the paper: [n] after the Ans: line.
    await waitFor(() => expect(shown(templated)).toEqual({ beside: '', line: '[3]' }))
    expect(shown(choice)).toEqual({ beside: '[3]', line: '' }) // no Ans: line: beside instead
    expect(shown(single)).toEqual({ beside: '', line: '[2]' })
    expect(shown(parts)).toEqual({ beside: '', line: '[4]' })
    await waitFor(() => expect(fragment(bank)).toBe('placement=answer'))
    await waitFor(() => expect(fragment(multi)).toBe('placement=answer'))

    // "Marks shown: In the header only" hides every [n] in the section, at once.
    setSection({ marks_placement: 'none' })
    await waitFor(() => expect(shown(templated)).toEqual({ beside: '', line: '' }))
    expect(shown(choice)).toEqual({ beside: '', line: '' })
    expect(shown(single)).toEqual({ beside: '', line: '' })
    expect(shown(parts)).toEqual({ beside: '', line: '' })
    await waitFor(() => expect(fragment(bank)).toBe('placement=none'))
    await waitFor(() => expect(fragment(multi)).toBe('placement=none'))
    // The question before the first section keeps the paper's placement.
    expect(shown(before)).toEqual({ beside: '', line: '[5]' })

    // "Beside each question".
    setSection({ marks_placement: 'question' })
    await waitFor(() => expect(shown(templated)).toEqual({ beside: '[3]', line: '' }))
    expect(shown(choice)).toEqual({ beside: '[3]', line: '' })
    expect(shown(single)).toEqual({ beside: '[2]', line: '' })
    expect(shown(parts)).toEqual({ beside: '[4]', line: '' })
    await waitFor(() => expect(fragment(bank)).toBe('placement=question'))

    // Back to the default, then a mode change: a short-answer section shows none.
    setSection({ marks_placement: null, mode: 'short' })
    await waitFor(() => expect(shown(templated)).toEqual({ beside: '', line: '' }))
    expect(shown(single)).toEqual({ beside: '', line: '' })
    setSection({ mode: null })
    await waitFor(() => expect(shown(templated)).toEqual({ beside: '', line: '[3]' }))

    // The paper-wide setting reaches sections that follow it, and the questions before them.
    paperSettings.set({ marks_placement: 'both' })
    await waitFor(() => expect(shown(templated)).toEqual({ beside: '[3]', line: '[3]' }))
    expect(shown(single)).toEqual({ beside: '[2]', line: '[2]' })
    expect(shown(parts)).toEqual({ beside: '[4]', line: '[4]' })
    expect(shown(before)).toEqual({ beside: '[5]', line: '[5]' })
  })

  it('a question moved out of a section takes the placement where it lands', async () => {
    make([
      { type: 'paragraph' },
      sectionNode('Booklet A', { mode: 'mcq' }),
      block(freeformDocNode({ marks: 2 }), 'moving'),
    ])
    await waitFor(() => expect(shown('moving')).toEqual({ beside: '', line: '' }))
    // Move the question above the section, as the drag handle or "Move up" does.
    const { doc } = editor.state
    let from = -1
    doc.forEach((n, offset) => {
      if (n.attrs.block_id === 'moving') from = offset
    })
    const node = doc.nodeAt(from)!
    editor.view.dispatch(editor.state.tr.delete(from, from + node.nodeSize).insert(0, node))
    await waitFor(() => expect(shown('moving')).toEqual({ beside: '', line: '[2]' }))
  })
})
