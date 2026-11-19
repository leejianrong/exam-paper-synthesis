import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/svelte'
import AnswerKey from './AnswerKey.svelte'
import { cleanNode } from './doc'
import { freeformDocNode, makeQuestion, templatedNodes } from './fixtures'
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

  const blocks = () => [
    ...templatedNodes([makeQuestion({ id: 'a' })]),
    freeformDocNode({ id: 'ff_9', marks: 2, body: 'FREEFORM-BODY', answer: 'ANS' }),
  ]

  it('hides the question text and the marking breakdown in the key view', () => {
    const { rerender } = render(AnswerKey, { props: { blocks: blocks() } })
    expect(document.body).toHaveTextContent('FREEFORM-BODY')
    expect(document.querySelector('.scheme')).not.toBeNull()
    rerender({ blocks: blocks(), options: { show_question: false, show_scheme: false, layout: 'full', show_marks: false, one_mark_working: true } })
    expect(document.body).not.toHaveTextContent('FREEFORM-BODY')
    expect(document.querySelector('.scheme')).toBeNull()
  })

  it('shows a left-out question dimmed, unchecked and still numbered', () => {
    const left = blocks()
    left[1] = { ...left[1], attrs: { ...(left[1].attrs as object), in_key: false } } as unknown as (typeof left)[number]
    render(AnswerKey, { props: { blocks: left } })
    const boxes = document.querySelectorAll<HTMLInputElement>('.incl input')
    expect(boxes[0].checked).toBe(true)
    expect(boxes[1].checked).toBe(false)
    expect(document.querySelectorAll('.entry')[1]).toHaveClass('excluded')
    expect(document.querySelectorAll('.entry')[1]).toHaveTextContent('2.')
  })
})
