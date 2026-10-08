import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/svelte'
import { get } from 'svelte/store'
import AccountChip from './AccountChip.svelte'
import { session } from '../session'

const fetchMock = vi.fn()
beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
  session.set({ status: 'user', user: { id: 'u1', email: 'ann@example.com', name: 'Ann', dev: false } })
})
afterEach(() => vi.unstubAllGlobals())

describe('AccountChip', () => {
  it('is hidden for the development stub', () => {
    session.set({ status: 'user', user: { id: 'local', email: null, name: 'Local', dev: true } })
    render(AccountChip)
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('downloads the data zip from the API', async () => {
    const click = vi.fn()
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(click)
    URL.createObjectURL = vi.fn(() => 'blob:x')
    URL.revokeObjectURL = vi.fn()
    fetchMock.mockResolvedValue({ ok: true, status: 200, blob: async () => new Blob(['zip']) })
    render(AccountChip)
    await fireEvent.click(screen.getByRole('button', { name: 'Ann' }))
    await fireEvent.click(screen.getByRole('button', { name: 'Download my data' }))
    expect(fetchMock).toHaveBeenCalledWith(expect.stringMatching(/\/account\/export$/), expect.anything())
    expect(click).toHaveBeenCalled()
  })

  it('deletes only after DELETE is typed, then drops the session', async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 204 })
    render(AccountChip)
    await fireEvent.click(screen.getByRole('button', { name: 'Ann' }))
    await fireEvent.click(screen.getByRole('button', { name: /Delete my account/ }))
    const confirm = screen.getByRole('button', { name: 'Delete everything' })
    expect(confirm).toBeDisabled()
    await fireEvent.input(screen.getByLabelText(/to confirm/), { target: { value: 'delete' } })
    expect(confirm).toBeDisabled()
    await fireEvent.input(screen.getByLabelText(/to confirm/), { target: { value: 'DELETE' } })
    await fireEvent.click(confirm)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toMatch(/\/account$/)
    expect(init.method).toBe('DELETE')
    expect(JSON.parse(init.body)).toEqual({ confirm: 'DELETE' })
    expect(get(session).status).toBe('anon')
  })

  it('keeps the session and says so when deletion fails', async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500 })
    render(AccountChip)
    await fireEvent.click(screen.getByRole('button', { name: 'Ann' }))
    await fireEvent.click(screen.getByRole('button', { name: /Delete my account/ }))
    await fireEvent.input(screen.getByLabelText(/to confirm/), { target: { value: 'DELETE' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Delete everything' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Nothing was changed')
    expect(get(session).status).toBe('user')
  })

  it('cancelling the confirmation returns to the menu without calling the API', async () => {
    render(AccountChip)
    await fireEvent.click(screen.getByRole('button', { name: 'Ann' }))
    await fireEvent.click(screen.getByRole('button', { name: /Delete my account/ }))
    await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.getByRole('button', { name: 'Download my data' })).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
