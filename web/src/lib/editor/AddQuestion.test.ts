import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/svelte'
import { makeQuestion } from './fixtures'

import AddQuestion from './AddQuestion.svelte'

// The picker is exercised through the real api.ts with fetch stubbed. (Rejecting a
// vi.mock()ed api function the component handles is reported by Vitest 4 as an unhandled
// error; a failing HTTP response is not.)
const fetchMock = vi.fn()
beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => vi.unstubAllGlobals())

const ok = (body: unknown) => ({ ok: true, status: 200, json: async () => body })

describe('AddQuestion picker', () => {
  it('generates three candidates for the chosen topic and difficulty, then inserts one', async () => {
    const candidates = [1, 2, 3].map((n) => makeQuestion({ id: `c${n}` }, `Candidate ${n}.`))
    fetchMock.mockResolvedValue(ok({ questions: candidates }))
    const insert = vi.fn()
    render(AddQuestion, { props: {}, events: { insert } })

    await fireEvent.change(screen.getByLabelText('Topic'), { target: { value: 'speed' } })
    await fireEvent.change(screen.getByLabelText('Difficulty'), { target: { value: 'hard' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Generate' }))

    await waitFor(() => expect(screen.getAllByTestId('candidate')).toHaveLength(3))
    const body = JSON.parse(fetchMock.mock.calls[0][1].body)
    expect(body).toEqual({ blueprint_code: 'speed_hard', count: 3 })

    await fireEvent.click(screen.getAllByRole('button', { name: 'Use this' })[1])
    expect(insert.mock.calls[0][0].detail.question.id).toBe('c2')
  })

  it('shows an API error and keeps the dialog open', async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500, text: async () => 'down' })
    render(AddQuestion, { props: {} })
    await fireEvent.click(screen.getByRole('button', { name: 'Generate' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('API 500: down')
  })

  it('offers the later tabs disabled, and Escape closes', async () => {
    const close = vi.fn()
    render(AddQuestion, { props: {}, events: { close } })
    expect(screen.getByRole('tab', { name: 'From my bank' })).toBeDisabled()
    expect(screen.getByRole('tab', { name: 'Free-form' })).toBeDisabled()
    await fireEvent.keyDown(window, { key: 'Escape' })
    expect(close).toHaveBeenCalled()
  })
})
