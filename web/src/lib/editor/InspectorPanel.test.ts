import { describe, it, expect } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/svelte'
import Inspector from './Inspector.svelte'
import { freeformDocNode, makeQuestion, templatedNodes } from './fixtures'

describe('Inspector remarks (W5)', () => {
  const blocks = () => [...templatedNodes([makeQuestion()]), freeformDocNode({ id: 'ff_9', marks: 2 })]

  it('offers a remarks box for the selected question, saying it never prints', () => {
    const [q] = blocks()
    render(Inspector, { props: { blocks: blocks(), marks: 5, selectedId: String(q.attrs?.block_id) } })
    expect(screen.getByLabelText(/Remarks/)).toBeInTheDocument()
    expect(screen.getByText(/never printed/)).toBeInTheDocument()
  })

  it('shows the existing remark and reports edits with the block id', async () => {
    const [q, ff] = blocks()
    const withRemark = { ...ff, attrs: { ...ff.attrs, remark: 'ask Ms Tan' } }
    const seen: Array<{ blockId: string; remark: string }> = []
    render(Inspector, {
      props: { blocks: [q, withRemark], marks: 5, selectedId: 'ff_9' },
      events: { remark: (e: CustomEvent) => seen.push(e.detail) },
    })
    const box = screen.getByLabelText(/Remarks/) as HTMLTextAreaElement
    expect(box.value).toBe('ask Ms Tan')
    await fireEvent.input(box, { target: { value: 'ask Ms Tan about units' } })
    expect(seen).toEqual([{ blockId: 'ff_9', remark: 'ask Ms Tan about units' }])
  })

  it('has no remarks box when no question is selected, but counts remarks in the summary', () => {
    const [q, ff] = blocks()
    render(Inspector, {
      props: { blocks: [{ ...q, attrs: { ...q.attrs, remark: 'x' } }, ff], marks: 5, selectedId: null },
    })
    expect(screen.queryByLabelText(/Remarks/)).toBeNull()
    expect(screen.getByText('Remarks')).toBeInTheDocument()
  })
})
