import { describe, it, expect } from 'vitest'
import { buildDocument, newBlockId, questionsOf, totalMarks, type DocJSON } from './doc'
import { makeQuestion } from './fixtures'

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
    expect(out.schema_version).toBe('1.0.0')
    expect(out.title).toBe('T')
  })
})
