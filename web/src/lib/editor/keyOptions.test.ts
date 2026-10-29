import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/svelte'
import AnswerKey from './AnswerKey.svelte'
import { cleanNode } from './doc'
import { freeformDocNode, makeQuestion, templatedNodes } from './fixtures'
import { keyOptionsOf } from './layout'

describe('answer-key options (P5)', () => {
  it('default to the full key and read what is set', () => {
    expect(keyOptionsOf(undefined)).toEqual({ show_question: true, show_scheme: true })
    expect(keyOptionsOf({ key_options: { show_scheme: false } })).toEqual({
      show_question: true,
      show_scheme: false,
    })
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
    rerender({ blocks: blocks(), options: { show_question: false, show_scheme: false } })
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
