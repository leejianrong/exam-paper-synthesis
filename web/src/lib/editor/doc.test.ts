import { describe, it, expect } from 'vitest'
import {
  blocksToHtml,
  buildDocument,
  cleanNode,
  freeformNode,
  newBlockId,
  normalizeAnswer,
  numberedNodes,
  questionsOf,
  totalMarks,
  type DocJSON,
  type DocNode,
} from './doc'
import { freeformDocNode, makeQuestion } from './fixtures'

const block = (id: string, q = makeQuestion()) => ({
  type: 'templatedQuestion',
  attrs: { block_id: id, question: q },
})

describe('document helpers', () => {
  it('newBlockId matches the server pattern and is unique', () => {
    const ids = new Set(Array.from({ length: 50 }, newBlockId))
    expect(ids.size).toBe(50)
    for (const id of ids) expect(id).toMatch(/^[A-Za-z0-9_-]{4,64}$/)
  })

  it('collects questions in order and sums marks', () => {
    const doc: DocJSON = {
      type: 'doc',
      content: [{ type: 'paragraph' }, block('b_1', makeQuestion({ id: 'x' })), block('b_2')],
    }
    expect(questionsOf(doc).map((q) => q.id)).toEqual(['x', 'ratio_medium:1'])
    expect(totalMarks(doc)).toBe(6)
  })

  it('buildDocument gives repeated block ids a fresh id (copy/paste duplicates)', () => {
    const out = buildDocument('T', {
      type: 'doc',
      content: [block('b_same'), { type: 'paragraph' }, block('b_same'), block('')],
    })
    const ids = out.content.content.filter((n) => n.type === 'templatedQuestion').map((n) => n.attrs?.block_id)
    expect(new Set(ids).size).toBe(3)
    expect(ids[0]).toBe('b_same')
    expect(out.schema_version).toBe('1.3.0')
    expect(out.title).toBe('T')
  })
})


describe('remarks (W5)', () => {
  const build = (node: DocNode) => buildDocument('T', { type: 'doc', content: [node] }).content.content[0]

  it('keeps a trimmed remark on either kind of question', () => {
    const t = block('b_1')
    const f = freeformDocNode({ id: 'ff_1' })
    expect(build({ ...t, attrs: { ...t.attrs, remark: '  check units  ' } }).attrs?.remark).toBe('check units')
    expect(build({ ...f, attrs: { ...f.attrs, remark: 'ask Ms Tan' } }).attrs?.remark).toBe('ask Ms Tan')
  })

  it('drops an unset, null or blank remark (the schema takes only a non-empty string)', () => {
    const t = block('b_1')
    for (const remark of [null, undefined, '', '   ']) {
      expect(build({ ...t, attrs: { ...t.attrs, remark } }).attrs).not.toHaveProperty('remark')
    }
  })
})

describe('free-form helpers (W2a)', () => {
  it('counts free-form marks in the total and numbers both kinds together', () => {
    const doc: DocJSON = {
      type: 'doc',
      content: [block('b_1'), freeformDocNode({ marks: 4 }), freeformDocNode({ id: 'ff_2', marks: null })],
    }
    expect(totalMarks(doc)).toBe(3 + 4)
    expect(numberedNodes(doc)).toHaveLength(3)
    expect(questionsOf(doc)).toHaveLength(1)
  })

  it('gives repeated free-form block ids a fresh id too', () => {
    const out = buildDocument('T', {
      type: 'doc',
      content: [freeformDocNode({ id: 'ff_dup' }), freeformDocNode({ id: 'ff_dup' })],
    })
    const ids = out.content.content.map((n) => n.attrs?.block_id)
    expect(new Set(ids).size).toBe(2)
    expect(out.schema_version).toBe('1.3.0')
  })

  it('a new free-form node is empty, unmarked and has a valid id', () => {
    const n = freeformNode()
    expect(n.attrs?.marks).toBeNull()
    expect(String(n.attrs?.block_id)).toMatch(/^[A-Za-z0-9_-]{4,64}$/)
    expect(normalizeAnswer(n.attrs?.answer as DocJSON).content).toEqual([])
  })

  it('normalizeAnswer drops trailing empty paragraphs only', () => {
    const text = { type: 'paragraph', content: [{ type: 'text', text: 'x' }] }
    const out = normalizeAnswer({ type: 'doc', content: [{ type: 'paragraph' }, text, { type: 'paragraph' }] })
    expect(out.content).toHaveLength(2)
    expect(normalizeAnswer({ type: 'doc', content: [{ type: 'paragraph' }] }).content).toEqual([])
  })

  it('blocksToHtml escapes text and keeps marks and lists', () => {
    const html = blocksToHtml([
      { type: 'paragraph', content: [{ type: 'text', text: '<b>&', marks: [{ type: 'bold' }] }] },
      {
        type: 'bulletList',
        content: [{ type: 'listItem', content: [{ type: 'paragraph', content: [{ type: 'text', text: 'a' }] }] }],
      },
    ])
    expect(html).toBe('<p><strong>&lt;b&gt;&amp;</strong></p><ul><li><p>a</p></li></ul>')
  })

  it('blocksToHtml draws images from their asset and keeps math for typesetting (escaped)', () => {
    const html = blocksToHtml([
      {
        type: 'paragraph',
        content: [
          { type: 'text', text: 'Find ' },
          { type: 'math', attrs: { latex: 'a<b "q"' } },
        ],
      },
      { type: 'image', attrs: { asset_id: 'asset_0001', alt: 'A "fig"', width_pct: 40 } },
    ])
    expect(html).toContain('<span class="math-host" data-latex="a&lt;b &quot;q&quot;">a&lt;b &quot;q&quot;</span>')
    expect(html).toMatch(/<img src="[^"]*\/assets\/asset_0001" alt="A &quot;fig&quot;" style="width:40%">/)
  })
})

describe('cleanNode (editor-only attributes never reach the server)', () => {
  const li = { type: 'listItem', content: [{ type: 'paragraph' }] }

  it("drops TipTap's null list-style type and a default start from ordered lists", () => {
    const out = cleanNode({ type: 'orderedList', attrs: { start: 1, type: null }, content: [li] })
    expect(out).toEqual({ type: 'orderedList', content: [li] })
  })

  it('keeps a real start, and nothing else', () => {
    const out = cleanNode({ type: 'orderedList', attrs: { start: 7, type: null }, content: [li] })
    expect(out.attrs).toEqual({ start: 7 })
  })

  it('cleans lists nested in free-form bodies and answers, and through buildDocument', () => {
    const dirty = { type: 'orderedList', attrs: { start: 3, type: null }, content: [li] }
    const doc = buildDocument('T', {
      type: 'doc',
      content: [
        dirty,
        {
          type: 'freeformQuestion',
          attrs: { block_id: 'ff_c', marks: 1, answer: { type: 'doc', content: [dirty] } },
          content: [dirty],
        },
      ],
    })
    const [top, ff] = doc.content.content
    expect(top.attrs).toEqual({ start: 3 })
    expect(ff.content![0].attrs).toEqual({ start: 3 })
    expect((ff.attrs!.answer as DocJSON).content[0].attrs).toEqual({ start: 3 })
  })

  it('normalizeAnswer cleans too', () => {
    const out = normalizeAnswer({
      type: 'doc',
      content: [{ type: 'orderedList', attrs: { start: 1, type: null }, content: [li] }],
    })
    expect(out.content[0].attrs).toBeUndefined()
  })
})
