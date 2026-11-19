import { describe, it, expect } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/svelte'
import Inspector from './Inspector.svelte'
import { freeformDocNode, makeBankQuestion, makeQuestion, templatedNodes } from './fixtures'

describe('Inspector remarks (W5)', () => {
  const blocks = () => [...templatedNodes([makeQuestion()]), freeformDocNode({ id: 'ff_9', marks: 2 })]

  it('offers a remarks box for the selected question, saying it never prints', () => {
    const [q] = blocks()
    render(Inspector, { props: { blocks: blocks(), selectedId: String(q.attrs?.block_id) } })
    expect(screen.getByLabelText(/Remarks/)).toBeInTheDocument()
    expect(screen.getByText(/never printed/)).toBeInTheDocument()
  })

  it('names the selected question by its number on the paper (EXA-134)', () => {
    render(Inspector, { props: { blocks: blocks(), selectedId: 'ff_9', start: 16 } })
    expect(screen.getByText('Question 17')).toBeInTheDocument()
  })

  it('shows the existing remark and reports edits with the block id', async () => {
    const [q, ff] = blocks()
    const withRemark = { ...ff, attrs: { ...ff.attrs, remark: 'ask Ms Tan' } }
    const seen: Array<{ blockId: string; remark: string }> = []
    render(Inspector, {
      props: { blocks: [q, withRemark], selectedId: 'ff_9' },
      events: { remark: (e: CustomEvent) => seen.push(e.detail) },
    })
    const box = screen.getByLabelText(/Remarks/) as HTMLTextAreaElement
    expect(box.value).toBe('ask Ms Tan')
    await fireEvent.input(box, { target: { value: 'ask Ms Tan about units' } })
    expect(seen).toEqual([{ blockId: 'ff_9', remark: 'ask Ms Tan about units' }])
  })

  it('has no remarks box when no question is selected, and says how to pick one', () => {
    render(Inspector, { props: { blocks: blocks(), selectedId: null } })
    expect(screen.queryByLabelText(/Remarks/)).toBeNull()
    expect(screen.getByText(/Click a question/)).toBeInTheDocument()
  })

  it('offers review only for bank questions, and says it is a deliberate act', async () => {
    const [bank, generated] = templatedNodes([makeBankQuestion(), makeQuestion()])
    const view = render(Inspector, { props: { blocks: [bank, generated], selectedId: 'blk_0' } })
    expect(screen.getByRole('button', { name: /Mark as reviewed…/ })).toBeInTheDocument()
    await view.rerender({ blocks: [bank, generated], selectedId: 'blk_1' })
    expect(screen.queryByRole('button', { name: /Mark as reviewed…/ })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Withdraw review' })).toBeNull()
  })
})
