import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/svelte'
import { makeQuestion } from './fixtures'

import NumbersPopover from './NumbersPopover.svelte'

// Exercised through the real api.ts with fetch stubbed (see AddQuestion.test.ts for why).
const fetchMock = vi.fn()
beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => vi.unstubAllGlobals())

const paramsResponse = (numbers: unknown[]) => ({
  ok: true,
  status: 200,
  json: async () => ({ slots: [], numbers }),
})
const RATIO = { key: 'ratio', label: 'Ratio', list: true, minimum: 1, maximum: 9, sep: ':' }
const TOTAL = { key: 'total', label: 'Amount shared ($)', list: false, minimum: 12, maximum: 2000 }

describe('NumbersPopover (EXA-89)', () => {
  it('lists the free numbers with their labels and submits them as numbers', async () => {
    fetchMock.mockResolvedValue(paramsResponse([RATIO, TOTAL]))
    const apply = vi.fn()
    render(NumbersPopover, { props: { q: makeQuestion() }, events: { apply } })

    const total = (await screen.findByLabelText('Amount shared ($)')) as HTMLInputElement
    expect(total.value).toBe('90')
    expect(total).toHaveAttribute('min', '12')
    expect((screen.getByLabelText('Ratio, number 3') as HTMLInputElement).value).toBe('4')
    expect(screen.getAllByText(':')).toHaveLength(2)
    // the answer is worked out by the engine, shown but not editable
    expect(screen.getByLabelText('Answer now, worked out by the engine')).toHaveTextContent('$40')

    await fireEvent.input(total, { target: { value: '180' } })
    await fireEvent.input(screen.getByLabelText('Ratio, number 1'), { target: { value: '1' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Apply' }))
    await waitFor(() => expect(apply).toHaveBeenCalled())
    expect(apply.mock.calls[0][0].detail.changes).toEqual({ ratio: [1, 3, 4], total: 180 })
  })

  it('focuses the first field once drawn, and Escape closes', async () => {
    fetchMock.mockResolvedValue(paramsResponse([RATIO, TOTAL]))
    const close = vi.fn()
    render(NumbersPopover, { props: { q: makeQuestion() }, events: { close } })
    const first = await screen.findByLabelText('Ratio, number 1')
    await waitFor(() => expect(first).toHaveFocus())
    await fireEvent.keyDown(first, { key: 'Escape' })
    expect(close).toHaveBeenCalledTimes(1)
  })

  it("shows the engine's refusal inline", async () => {
    fetchMock.mockResolvedValue(paramsResponse([TOTAL]))
    const error = "The question wasn't changed. The amount must be a multiple of 9."
    render(NumbersPopover, { props: { q: makeQuestion(), error } })
    expect(await screen.findByRole('alert')).toHaveTextContent('The amount must be a multiple of 9.')
  })

  it('says so and disables Apply when no number can change', async () => {
    fetchMock.mockResolvedValue(paramsResponse([]))
    render(NumbersPopover, { props: { q: makeQuestion({ blueprint_code: 'ratio_hard' }) } })
    expect(await screen.findByText('No numbers in this question can be changed.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Apply' })).toBeDisabled()
  })
})
