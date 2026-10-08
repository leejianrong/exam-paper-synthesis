import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { get } from 'svelte/store'
import { apiFetch } from './http'
import { loadProviders, loadSession, loginUrl, session, sessionLost, signOut } from './session'

const fetchMock = vi.fn()
beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
  session.set({ status: 'loading' })
})
afterEach(() => vi.unstubAllGlobals())

const user = { id: 'u1', email: 'ann@example.com', name: 'Ann', dev: false }

describe('session', () => {
  it('asks /auth/me with credentials and becomes that user', async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => user })
    await loadSession()
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/auth\/me$/)
    expect(fetchMock.mock.calls[0][1].credentials).toBe('include')
    expect(get(session)).toEqual({ status: 'user', user })
  })

  it('401 means nobody is signed in; an unreachable API does too (login page, not a hang)', async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 401 })
    await loadSession()
    expect(get(session)).toEqual({ status: 'anon' })
    session.set({ status: 'loading' })
    fetchMock.mockRejectedValue(new Error('down'))
    await loadSession()
    expect(get(session)).toEqual({ status: 'anon' })
  })

  it('apiFetch always sends the cookie, and a 401 anywhere ends the session', async () => {
    session.set({ status: 'user', user })
    fetchMock.mockResolvedValue({ ok: true, status: 200 })
    await apiFetch('http://x/documents', { method: 'POST', body: '{}' })
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: 'POST', credentials: 'include' })
    expect(get(session).status).toBe('user')

    fetchMock.mockResolvedValue({ ok: false, status: 401 })
    await apiFetch('http://x/documents')
    expect(get(session)).toEqual({ status: 'anon' })
  })

  it('sign-out posts to the server and drops the session even if that fails', async () => {
    session.set({ status: 'user', user })
    fetchMock.mockRejectedValue(new Error('offline'))
    await expect(signOut()).rejects.toThrow()
    expect(get(session)).toEqual({ status: 'anon' })
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/auth\/logout$/)
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: 'POST', credentials: 'include' })
  })

  it('providers and login URLs', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({ providers: [{ name: 'github', label: 'GitHub' }], dev: false }) })
    expect((await loadProviders()).providers[0].name).toBe('github')
    expect(loginUrl('google')).toMatch(/\/auth\/google\/login$/)
    sessionLost()
    expect(get(session).status).toBe('anon')
  })
})
