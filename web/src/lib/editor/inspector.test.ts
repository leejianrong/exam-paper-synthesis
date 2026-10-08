import { describe, it, expect } from 'vitest'
import { describeBlock, summarise } from './inspector'
import { freeformDocNode, makeBankQuestion, makeQuestion, templatedNodes } from './fixtures'

describe('describeBlock', () => {
  it('a generated question is engine-verified, with its blueprint and seed', () => {
    const f = describeBlock(templatedNodes([makeQuestion()])[0], 2)
    expect(f.heading).toBe('Question 2')
    expect(f.status.tone).toBe('ok')
    expect(f.status.text).toMatch(/Engine-verified/)
    expect(Object.fromEntries(f.rows)).toMatchObject({ Type: 'Generated', Blueprint: 'ratio_medium', Marks: '3' })
  })

  it('a failed validation is not called verified', () => {
    const f = describeBlock(templatedNodes([makeQuestion({ validation: { status: 'fail' } })])[0], 1)
    expect(f.status).toEqual({ text: 'Not verified', tone: 'warn' })
  })

  it('a bank question says whether you have reviewed it, and is never "engine-verified"', () => {
    const unreviewed = describeBlock(templatedNodes([makeBankQuestion()])[0], 1)
    expect(unreviewed.status.tone).toBe('warn')
    expect(unreviewed.status.text).toMatch(/not yet reviewed/)
    const reviewed = describeBlock(
      templatedNodes([makeBankQuestion({ validation: { status: 'pass', checks: { human_reviewed: true } } })])[0],
      1,
    )
    expect(reviewed.status.tone).toBe('ok')
    expect(reviewed.status.text).not.toMatch(/Engine-verified/)
  })

  it('a free-form question is plainly unchecked', () => {
    const f = describeBlock(freeformDocNode({ marks: null }), 1)
    expect(f.status.tone).toBe('plain')
    expect(f.status.text).toMatch(/not checked/)
    expect(Object.fromEntries(f.rows).Marks).toBe('Not set')
  })
})

describe('summarise', () => {
  it('counts each kind', () => {
    const blocks = [
      ...templatedNodes([makeQuestion(), makeBankQuestion()]),
      freeformDocNode(),
    ]
    expect(summarise(blocks, 8)).toEqual({ questions: 3, generated: 1, bank: 1, freeform: 1, marks: 8 })
  })
})
