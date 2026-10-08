import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/svelte'
import { makeQuestion } from './fixtures'

import NamesPopover from './NamesPopover.svelte'

// Exercised through the real api.ts with fetch stubbed (see AddQuestion.test.ts for why).
const fetchMock = vi.fn()
beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => vi.unstubAllGlobals())

const slotsResponse = (slots: unknown[]) => ({ ok: true, status: 200, json: async () => ({ slots }) })

describe('NamesPopover', () => {
  it('builds one input per name from the slot metadata and submits the new names', async () => {
    fetchMock.mockResolvedValue(slotsResponse([{ key: 'names', role: 'name', count: 3, max_length: 24 }]))
    const apply = vi.fn()
    render(NamesPopover, { props: { q: makeQuestion() }, events: { apply } })

    const first = (await screen.findByLabelText('Name 1')) as HTMLInputElement
    expect(first.value).toBe('Ann')
    expect((screen.getByLabelText('Name 3') as HTMLInputElement).value).toBe('Cal')
    expect(first).toHaveAttribute('maxlength', '24')

    await fireEvent.input(first, { target: { value: 'Zara' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Apply' }))
    await waitFor(() => expect(apply).toHaveBeenCalled())
    expect(apply.mock.calls[0][0].detail.changes).toEqual({ names: ['Zara', 'Ben', 'Cal'] })
  })

  it('sends a scalar for a single-name blueprint and a pooled select for an item', async () => {
    fetchMock.mockResolvedValue(slotsResponse([
      { key: 'name', role: 'name', count: 1, max_length: 24 },
      { key: 'context', role: 'item', count: 1, pool: ['bicycle', 'desk'] },
    ]))
    const q = makeQuestion({ parameters: { name: 'Ann', context: 'bicycle' } })
    const apply = vi.fn()
    render(NamesPopover, { props: { q }, events: { apply } })

    await fireEvent.input(await screen.findByLabelText('Name'), { target: { value: 'Ben' } })
    await fireEvent.change(screen.getByLabelText('Item'), { target: { value: 'desk' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Apply' }))
    await waitFor(() => expect(apply).toHaveBeenCalled())
    expect(apply.mock.calls[0][0].detail.changes).toEqual({ name: 'Ben', context: 'desk' })
  })

  it('says so and disables Apply when a blueprint has nothing to rename', async () => {
    fetchMock.mockResolvedValue(slotsResponse([]))
    render(NamesPopover, { props: { q: makeQuestion({ blueprint_code: 'geometry_angle_easy' }) } })
    expect(await screen.findByText('Nothing to rename in this question.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Apply' })).toBeDisabled()
  })

  it('shows the load error and disables Apply', async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 404, text: async () => 'nope' })
    render(NamesPopover, { props: { q: makeQuestion() } })
    expect(await screen.findByRole('alert')).toHaveTextContent('API 404: nope')
    expect(screen.getByRole('button', { name: 'Apply' })).toBeDisabled()
  })
})
