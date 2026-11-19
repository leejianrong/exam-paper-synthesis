import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/svelte'
import { ApiError, canRetry, errorText, fail, plainMessage, waitText } from './errors'
import { apiFetch } from './http'
import ErrorNote from './ErrorNote.svelte'

const res = (status: number, body: unknown, headers: Record<string, string> = {}): Response =>
  new Response(body === undefined ? null : JSON.stringify(body), { status, headers })

beforeEach(() => vi.spyOn(console, 'warn').mockImplementation(() => {}))
afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('plainMessage (EXA-165): every status class in words, no codes', () => {
  it.each([
    [0, null, "Can't reach the server. Check your internet connection."],
    [401, 'authentication required', "You're signed out. Sign in again to carry on."],
    [403, 'forbidden', "You don't have access to this."],
    [404, 'document not found', "This paper doesn't exist or was deleted."],
    [404, 'folder not found', "This folder doesn't exist or was deleted."],
    [404, 'what', "It doesn't exist any more or was deleted."],
    [409, { message: 'document changed elsewhere', current_version: 5 }, 'This paper changed in another tab or window. Reload to get the latest version.'],
    [413, 'image is larger than 2 MB', 'Image is larger than 2 MB.'],
    [413, null, 'That is too large to send.'],
    [422, 'name must be 1-80 characters', 'Name must be 1-80 characters.'],
    [422, 'invalid question: x', "The server couldn't accept this, so nothing was changed."],
    [422, [{ loc: ['body'], msg: 'field required' }], "The server couldn't accept this, so nothing was changed."],
    [500, 'Traceback …', 'Something went wrong on our side. Try again in a moment.'],
    [502, null, 'Something went wrong on our side. Try again in a moment.'],
    [503, 'database unavailable', 'The server is busy. Try again in a moment.'],
  ])('%i %j', (status, detail, text) => {
    expect(plainMessage(status, detail)).toBe(text)
  })

  it('a sentence the server wrote for people is shown as it is', () => {
    expect(plainMessage(422, 'This question is locked. Unlock it to swap it.')).toBe('This question is locked. Unlock it to swap it.')
    expect(plainMessage(409, { code: 'unfilled_placeholders', message: 'Question 3 is still empty.' })).toBe('Question 3 is still empty.')
    expect(plainMessage(429, 'Export limit reached for this minute. Try again in 40 seconds.', 40)).toBe(
      'Export limit reached for this minute. Try again in 40 seconds.',
    )
  })

  it('429 says how long to wait, from Retry-After', () => {
    expect(plainMessage(429, 'too many requests', 30)).toBe('Too many requests. Try again in 30 seconds.')
    expect(plainMessage(429, 'too many requests', 120)).toBe('Too many requests. Try again in 2 minutes.')
    expect(plainMessage(429, 'too many requests')).toBe('Too many requests. Try again in a minute.')
    expect(waitText(1)).toBe('1 second')
    expect(waitText(7200)).toBe('2 hours')
  })
})

describe('fail and apiFetch', () => {
  it('fail throws an ApiError with the detail and Retry-After kept off the message', async () => {
    const err = await fail(res(429, { detail: 'too many requests' }, { 'retry-after': '45' })).catch((e: unknown) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err).toMatchObject({ status: 429, detail: 'too many requests', retryAfter: 45 })
    expect((err as Error).message).toBe('Too many requests. Try again in 45 seconds.')
  })

  it('a body that is not JSON keeps the status text as the detail', async () => {
    const err = (await fail(new Response('<html>', { status: 502, statusText: 'Bad Gateway' })).catch((e: unknown) => e)) as ApiError
    expect(err.detail).toBe('Bad Gateway')
    expect(err.message).toBe('Something went wrong on our side. Try again in a moment.')
  })

  it('apiFetch turns a network failure into ApiError(0)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    const err = await apiFetch('http://x/documents').catch((e: unknown) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err).toMatchObject({ status: 0, message: "Can't reach the server. Check your internet connection." })
  })
})

describe('canRetry and errorText', () => {
  it('offers Try again only when the same request may work now', () => {
    expect(canRetry(new ApiError(0, ''))).toBe(true)
    expect(canRetry(new ApiError(429, '', 5))).toBe(true)
    expect(canRetry(new ApiError(500, ''))).toBe(true)
    expect(canRetry(new ApiError(503, ''))).toBe(true)
    for (const s of [401, 403, 404, 409, 413, 422]) expect(canRetry(new ApiError(s, ''))).toBe(false)
    expect(canRetry(new Error('x'))).toBe(false)
  })

  it('says what did not happen, then why', () => {
    expect(errorText(new ApiError(500, 'boom'), "Couldn't save")).toBe(
      "Couldn't save. Something went wrong on our side. Try again in a moment.",
    )
    expect(errorText(new Error('Your latest changes are not saved yet.'))).toBe('Your latest changes are not saved yet.')
    expect(errorText('???', 'The paper wasn’t moved')).toBe('The paper wasn’t moved. Something unexpected went wrong. Try again.')
  })
})

describe('ErrorNote', () => {
  it('is an alert with the message, and Try again only when there is a retry', async () => {
    const onRetry = vi.fn()
    const { rerender } = render(ErrorNote, { props: { message: 'Couldn’t load your papers.' } })
    expect(screen.getByRole('alert')).toHaveTextContent('Couldn’t load your papers.')
    expect(screen.queryByRole('button')).toBeNull()
    await rerender({ message: 'Couldn’t load your papers.', onRetry })
    await fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(onRetry).toHaveBeenCalledOnce()
    await rerender({ message: 'x', onRetry, busy: true })
    expect(screen.getByRole('button', { name: 'Trying…' })).toBeDisabled()
  })
})
