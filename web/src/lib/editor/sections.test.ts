import { describe, it, expect } from 'vitest'
import { buildDocument, cleanNode, paperOutline, type DocJSON } from './doc'
import { freeformDocNode } from './fixtures'
import { markingOn, sectionNode, sectionSummary, targetState } from './sections'
import { PAPER_TEMPLATES, buildFromTemplate } from './templates'

const doc = (...content: DocJSON['content']): DocJSON => ({ type: 'doc', content })

describe('paperOutline', () => {
  const content = doc(
    freeformDocNode({ marks: 1 }),
    sectionNode('A', { marks_target: 5 }),
    freeformDocNode({ marks: 2 }),
    freeformDocNode({ marks: 3 }),
    { type: 'paragraph' },
    sectionNode('B'),
    freeformDocNode({ marks: 4 }),
    sectionNode('Empty'),
  )

  it('derives ranges and marks, continuing numbers, ignoring questions before a section', () => {
    const [a, b, empty] = paperOutline(content)
    expect(a).toMatchObject({ first: 2, last: 3, count: 2, marks: 5, target: 5 })
    expect(b).toMatchObject({ first: 4, last: 4, count: 1, marks: 4, target: null })
    expect(empty).toMatchObject({ first: null, count: 0, marks: 0 })
  })

  it('summarises a section and flags a target mismatch', () => {
    const [a, b, empty] = paperOutline(content)
    expect(sectionSummary(a)).toBe('Questions 2–3 · 5 / 5 marks')
    expect(sectionSummary(b)).toBe('Question 4 · 4 marks')
    expect(sectionSummary(empty)).toBe('No questions yet')
    expect(targetState(a)).toBe('ok')
    expect(targetState({ ...a, target: 4 })).toBe('over')
    expect(targetState({ ...a, target: 9 })).toBe('under')
    expect(targetState(empty)).toBe('ok')
  })
})

describe('section serialisation', () => {
  it('drops unset optional attrs and keeps the title a string', () => {
    const out = cleanNode({
      type: 'section',
      attrs: { title: null, instructions: '  ', mode: null, marks_target: null },
    })
    expect(out.attrs).toEqual({ title: '' })
    const full = cleanNode(sectionNode('A', { mode: 'mcq', marks_target: 0, instructions: ' hi ' }))
    expect(full.attrs).toEqual({ title: 'A', instructions: 'hi', mode: 'mcq', marks_target: 0 })
  })
})

describe('marking margin (P6a)', () => {
  it('follows the mode unless the author chose', () => {
    expect(markingOn({ mode: 'short' })).toBe(true)
    expect(markingOn({ mode: 'structured' })).toBe(true)
    expect(markingOn({ mode: 'mcq' })).toBe(false)
    expect(markingOn({})).toBe(false)
    expect(markingOn({ mode: 'mcq', marking: true })).toBe(true)
    expect(markingOn({ mode: 'short', marking: false })).toBe(false)
  })

  it('stores only an explicit choice', () => {
    expect(cleanNode(sectionNode('A')).attrs).toEqual({ title: 'A' })
    const on = cleanNode({ type: 'section', attrs: { title: 'A', marking: true } })
    const off = cleanNode({ type: 'section', attrs: { title: 'A', marking: false } })
    expect(on.attrs).toHaveProperty('marking', true)
    expect(off.attrs).toHaveProperty('marking', false)
  })
})

describe('starter templates', () => {
  it('are three plain documents with sections, a target and a paper time', () => {
    expect(PAPER_TEMPLATES.map((t) => t.id)).toEqual(['p1-a', 'p1-b', 'p2'])
    for (const t of PAPER_TEMPLATES) {
      const d = buildFromTemplate(t)
      expect(d.title).toBe(t.title)
      expect(d.settings?.time_min).toBeGreaterThan(0)
      expect(d.content.content.every((n) => n.type === 'section')).toBe(true)
      expect(paperOutline(d.content).every((s) => (s.target ?? 0) > 0)).toBe(true)
    }
    const p2 = paperOutline(buildFromTemplate(PAPER_TEMPLATES[2]).content)
    expect(p2.map((s) => s.target)).toEqual([10, 45])
  })

  it('buildDocument keeps sections and the paper time', () => {
    const out = buildDocument('T', doc(sectionNode('A')), { time_min: 30 })
    expect(out.content.content[0].type).toBe('section')
    expect(out.settings).toEqual({ time_min: 30 })
  })
})
