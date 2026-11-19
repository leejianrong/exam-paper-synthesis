import { describe, it, expect } from 'vitest'
import type { BankItem } from './api'
import { filterBank, filterOptions, isFiltered, NO_FILTERS, type BankFilters } from './bank'
import { makeBankQuestion } from './editor/fixtures'

const item = (over: Partial<BankItem> & { id: string }, text = 'Which shape has four equal sides?'): BankItem => ({
  topic: 'Ratio',
  level: 'P6',
  difficulty: 'medium',
  source_type: 'sourced',
  reviewed: false,
  question: makeBankQuestion({ id: over.id, question: { total_marks: 1, parts: [{ text, marks: 1 }] } }),
  ...over,
})

const ITEMS = [
  item({ id: 'a', reviewed: true }, 'Ann and Ben share sweets.'),
  item({ id: 'b', topic: 'Geometry', level: 'P5', difficulty: 'hard' }, 'Find angle x.'),
  item({ id: 'c', difficulty: 'easy' }, 'Café prices'),
  item({ id: 'd', source_type: 'generated', topic: 'Speed', difficulty: null }),
]
const ids = (f: Partial<BankFilters>) => filterBank(ITEMS, { ...NO_FILTERS, ...f }).map((i) => i.id)

describe('bank filters (EXA-167)', () => {
  it('offers only values the bank holds, difficulties in their order', () => {
    expect(filterOptions(ITEMS)).toEqual({
      topics: ['Geometry', 'Ratio', 'Speed'],
      levels: ['P5', 'P6'],
      difficulties: ['easy', 'medium', 'hard'],
      sources: ['generated', 'sourced'],
    })
  })

  it('filters by topic, level, difficulty and source', () => {
    expect(ids({})).toEqual(['a', 'b', 'c', 'd'])
    expect(ids({ topic: 'Ratio' })).toEqual(['a', 'c'])
    expect(ids({ level: 'P5' })).toEqual(['b'])
    expect(ids({ difficulty: 'easy' })).toEqual(['c'])
    expect(ids({ source: 'generated' })).toEqual(['d'])
    expect(ids({ topic: 'Ratio', difficulty: 'medium' })).toEqual(['a'])
  })

  it('"Not reviewed" is an imported question not yet checked; a generated one needs no review', () => {
    expect(ids({ review: 'reviewed' })).toEqual(['a'])
    expect(ids({ review: 'unreviewed' })).toEqual(['b', 'c'])
  })

  it('searches the question text, topic and id, ignoring case and accents', () => {
    expect(ids({ query: 'ANGLE' })).toEqual(['b'])
    expect(ids({ query: 'cafe' })).toEqual(['c'])
    expect(ids({ query: 'geometry' })).toEqual(['b'])
    expect(ids({ query: 'ann sweets' })).toEqual(['a'])
    expect(ids({ query: '   ' })).toEqual(['a', 'b', 'c', 'd'])
  })

  it('knows when any filter is set', () => {
    expect(isFiltered(NO_FILTERS)).toBe(false)
    expect(isFiltered({ ...NO_FILTERS, query: '  ' })).toBe(false)
    expect(isFiltered({ ...NO_FILTERS, level: 'P5' })).toBe(true)
  })
})
