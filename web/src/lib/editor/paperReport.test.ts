import { describe, it, expect } from 'vitest'
import { reportSummary, unfilledPlaceholders } from './paperReport'
import type { PaperReport } from './docsApi'
import type { DocJSON } from './doc'

const section = (o: Partial<PaperReport['sections'][number]>) => ({
  title: 'S',
  mode: 'short',
  marks_target: 10,
  slots: 5,
  filled: 5,
  stand_ins: 0,
  placeholders: 0,
  placeholder_marks: 0,
  ...o,
})

const report = (o: Partial<PaperReport>): PaperReport => ({
  template: 'p2',
  level: 'P6',
  seed: 1,
  title: 'P6 Paper 2',
  filled: 19,
  placeholders: 0,
  placeholder_marks: 0,
  sections: [],
  topics: {},
  ...o,
})

describe('reportSummary', () => {
  it('says what was filled and what is left, honestly', () => {
    expect(
      reportSummary(
        report({
          filled: 10,
          placeholders: 5,
          placeholder_marks: 8,
          sections: [section({ title: 'Booklet B', filled: 10, placeholders: 5 })],
        }),
      ),
    ).toBe('Filled 10 of 15 questions from the question generator. 5 placeholders (8 marks) left for you to write or replace.')
  })

  it('names stand-ins and the missing multiple choice', () => {
    const text = reportSummary(
      report({
        filled: 0,
        placeholders: 1,
        placeholder_marks: 1,
        sections: [
          section({ title: 'Section B', mode: 'structured', stand_ins: 1 }),
          section({ title: 'Booklet A', mode: 'mcq', placeholders: 1 }),
        ],
      }),
    )
    expect(text).toContain('1 placeholder (1 mark)')
    expect(text).toContain('Section B uses 1 single-part question in place of multi-part ones.')
    expect(text).toContain("Booklet A: multiple-choice questions can't be generated yet.")
  })
})

describe('unfilledPlaceholders', () => {
  const ph = (text?: string) => ({
    type: 'freeformQuestion',
    attrs: { block_id: 'b1', marks: 2, slot: { marks: 2, kind: 'short', placeholder: true } },
    content: [{ type: 'paragraph', ...(text ? { content: [{ type: 'text', text }] } : {}) }],
  })
  it('counts placeholders whose body is still empty', () => {
    const doc: DocJSON = {
      type: 'doc',
      content: [ph(), ph('  '), ph('Ann has 3 apples.'), { type: 'freeformQuestion', attrs: { marks: 1 }, content: [{ type: 'paragraph' }] }],
    }
    expect(unfilledPlaceholders(doc)).toBe(2)
  })

  it('a placeholder written only in its parts, or with only a figure, counts as written', () => {
    const base = ph()
    const withPart = {
      ...base,
      content: [
        { type: 'paragraph' },
        { type: 'freeformPart', attrs: { marks: 2 }, content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Find x.' }] }] },
      ],
    }
    const withImage = { ...base, content: [{ type: 'image', attrs: { asset_id: 'a1' } }] }
    const emptyPart = { ...base, content: [{ type: 'paragraph' }, { type: 'freeformPart', attrs: {}, content: [{ type: 'paragraph' }] }] }
    expect(unfilledPlaceholders({ type: 'doc', content: [withPart, withImage, emptyPart] })).toBe(1)
  })
})

