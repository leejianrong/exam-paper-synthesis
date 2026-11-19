import { describe, it, expect } from 'vitest'
import { cleanNode } from './doc'
import { keyOptionsOf } from './layout'

describe('answer-key options (P5)', () => {
  it('absent options keep a saved paper as it printed, and read what is set', () => {
    const before = { show_question: true, show_scheme: true, layout: 'full', show_marks: false, one_mark_working: true }
    expect(keyOptionsOf(undefined)).toEqual(before)
    expect(keyOptionsOf({ key_options: { show_scheme: false } })).toEqual({ ...before, show_scheme: false })
    expect(keyOptionsOf({ key_options: { layout: 'compact' } }).layout).toBe('compact')
    // a new paper's school key (EXA-159), as the API writes it
    const school = { layout: 'compact' as const, show_scheme: false, show_marks: false, one_mark_working: false }
    expect(keyOptionsOf({ key_options: school })).toEqual({ ...school, show_question: true })
  })

  it('store in_key only when a question is left out', () => {
    const attrs = (v: unknown) =>
      cleanNode({ type: 'freeformQuestion', attrs: { block_id: 'ff_1', in_key: v } }).attrs
    expect(attrs(true)).not.toHaveProperty('in_key')
    expect(attrs(undefined)).not.toHaveProperty('in_key')
    expect(attrs(false)).toHaveProperty('in_key', false)
  })
})
