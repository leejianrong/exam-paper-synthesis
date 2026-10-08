import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/svelte'
import App from './App.svelte'
import { session, sessionLost } from './lib/session'

const fetchMock = vi.fn()
beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
  session.set({ status: 'loading' })
  globalThis.location.hash = '#/'
})
afterEach(() => vi.unstubAllGlobals())

const reply = (status: number, body: unknown = {}) => ({ ok: status < 400, status, json: async () => body, text: async () => '' })

function route(me: { status: number; body?: unknown }) {
  fetchMock.mockImplementation(async (url: string) => {
    if (String(url).endsWith('/auth/me')) return reply(me.status, me.body)
    if (String(url).endsWith('/auth/providers')) return reply(200, { providers: [{ name: 'google', label: 'Google' }], dev: false })
    if (String(url).endsWith('/documents')) return reply(200, { documents: [] })
    return reply(404)
  })
}

describe('App sign-in gate', () => {
  it('shows the login page when nobody is signed in', async () => {
    route({ status: 401 })
    render(App)
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Your papers' })).toBeNull()
  })

  it('shows the papers, with who you are and a sign-out, once signed in', async () => {
    route({ status: 200, body: { id: 'u1', email: 'ann@example.com', name: 'Ann', dev: false } })
    render(App)
    expect(await screen.findByRole('heading', { name: 'Your papers' })).toBeInTheDocument()
    expect(screen.getByText('Ann')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign out' })).toBeInTheDocument()
  })

  it('the local development stub needs no sign-in and has nothing to sign out of', async () => {
    route({ status: 200, body: { id: 'local', email: null, name: 'Local development', dev: true } })
    render(App)
    expect(await screen.findByRole('heading', { name: 'Your papers' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Sign out' })).toBeNull()
  })

  it('an expired session mid-use drops back to the login page', async () => {
    route({ status: 200, body: { id: 'u1', email: null, name: 'Ann', dev: false } })
    render(App)
    await screen.findByRole('heading', { name: 'Your papers' })
    sessionLost()
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
  })

  it('a failed provider sign-in lands on the login page with the reason', async () => {
    route({ status: 401 })
    globalThis.location.hash = '#/login?error=denied'
    render(App)
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Sign-in was cancelled.'))
  })
})
