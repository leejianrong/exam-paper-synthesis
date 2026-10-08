import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte'
import ReviewControl from './ReviewControl.svelte'

const fetchMock = vi.fn()
beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => vi.unstubAllGlobals())

const reply = (status: number, body = '') => ({ ok: status < 400, status, text: async () => body, json: async () => ({}) })

describe('ReviewControl (ADR-0019: review is a deliberate act)', () => {
  it('needs an explicit confirmation before marking reviewed, and calls the API once', async () => {
    fetchMock.mockResolvedValue(reply(200))
    const changed = vi.fn()
    render(ReviewControl, { props: { id: 'sourced:psle/2023 q1', reviewed: false }, events: { changed } })

    await fireEvent.click(screen.getByRole('button', { name: /Mark as reviewed…/ }))
    const go = screen.getByRole('button', { name: 'Mark as reviewed' })
    expect(go).toBeDisabled() // cannot be done in one click
    expect(fetchMock).not.toHaveBeenCalled()
    await fireEvent.click(screen.getByLabelText(/I have checked this question/))
    await fireEvent.click(go)

    await waitFor(() => expect(changed).toHaveBeenCalledTimes(1))
    expect(changed.mock.calls[0][0].detail).toEqual({ reviewed: true })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toMatch(/\/bank\/sourced%3Apsle%2F2023%20q1\/review$/)
    expect(init.method).toBe('PUT')
    expect(JSON.parse(init.body)).toEqual({ reviewed: true })
  })

  it('cancelling the confirmation changes nothing', async () => {
    render(ReviewControl, { props: { id: 's1', reviewed: false } })
    await fireEvent.click(screen.getByRole('button', { name: /Mark as reviewed…/ }))
    await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.getByRole('button', { name: /Mark as reviewed…/ })).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('withdraws a review in one click', async () => {
    fetchMock.mockResolvedValue(reply(200))
    const changed = vi.fn()
    render(ReviewControl, { props: { id: 's1', reviewed: true }, events: { changed } })
    await fireEvent.click(screen.getByRole('button', { name: 'Withdraw review' }))
    await waitFor(() => expect(changed).toHaveBeenCalled())
    expect(changed.mock.calls[0][0].detail).toEqual({ reviewed: false })
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ reviewed: false })
  })

  it('reports a server error and does not claim the review happened', async () => {
    fetchMock.mockResolvedValue(reply(500, 'boom'))
    const changed = vi.fn()
    render(ReviewControl, { props: { id: 's1', reviewed: false }, events: { changed } })
    await fireEvent.click(screen.getByRole('button', { name: /Mark as reviewed…/ }))
    await fireEvent.click(screen.getByLabelText(/I have checked/))
    await fireEvent.click(screen.getByRole('button', { name: 'Mark as reviewed' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('API 500: boom')
    expect(changed).not.toHaveBeenCalled()
  })

  it('a question gone from the bank is an error in the bank list but fine on a paper', async () => {
    fetchMock.mockResolvedValue(reply(404))
    const a = render(ReviewControl, { props: { id: 's1', reviewed: true } })
    await fireEvent.click(screen.getByRole('button', { name: 'Withdraw review' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('no longer in your bank')
    a.unmount()

    const changed = vi.fn()
    render(ReviewControl, { props: { id: 's1', reviewed: true, allowMissing: true }, events: { changed } })
    await fireEvent.click(screen.getByRole('button', { name: 'Withdraw review' }))
    await waitFor(() => expect(changed).toHaveBeenCalled())
  })
})
