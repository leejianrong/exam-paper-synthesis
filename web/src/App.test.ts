import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte'
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
    await fireEvent.click(screen.getByRole('button', { name: 'Account: Ann' }))
    expect(screen.getByText('Ann')).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: 'Sign out' })).toBeInTheDocument()
  })

  it('the local development stub needs no sign-in and has nothing to sign out of', async () => {
    route({ status: 200, body: { id: 'local', email: null, name: 'Local development', dev: true } })
    render(App)
    expect(await screen.findByRole('heading', { name: 'Your papers' })).toBeInTheDocument()
    await fireEvent.click(screen.getByRole('button', { name: 'Account: Local development' }))
    expect(screen.queryByRole('menuitem', { name: 'Sign out' })).toBeNull()
  })

  it('an expired session mid-use drops back to the login page', async () => {
    route({ status: 200, body: { id: 'u1', email: null, name: 'Ann', dev: false } })
    render(App)
    await screen.findByRole('heading', { name: 'Your papers' })
    sessionLost()
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
  })

  it('one app header on the list, the bank and Settings (EXA-167)', async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (String(url).endsWith('/auth/me')) return reply(200, { id: 'u1', email: null, name: 'Ann', dev: false })
      if (String(url).endsWith('/documents')) return reply(200, { documents: [] })
      if (String(url).endsWith('/bank')) return reply(200, { items: [] })
      if (String(url).endsWith('/settings')) return reply(200, { classic_generator: false, answer_key_style: 'school', school_name: '', default_level: '', marks_placement: 'answer' })
      return reply(404)
    })
    render(App)
    await screen.findByRole('heading', { name: 'Your papers' })
    expect(screen.getAllByRole('navigation', { name: 'Main' })).toHaveLength(1)
    globalThis.location.hash = '#/bank'
    await fireEvent(window, new HashChangeEvent('hashchange'))
    expect(await screen.findByRole('heading', { name: 'Question bank' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Question bank' })).toHaveAttribute('aria-current', 'page')
    globalThis.location.hash = '#/settings'
    await fireEvent(window, new HashChangeEvent('hashchange'))
    expect(await screen.findByRole('heading', { name: 'Settings' })).toBeInTheDocument()
    expect(screen.getAllByRole('navigation', { name: 'Main' })).toHaveLength(1)
    expect(screen.queryByRole('link', { name: '← Your papers' })).toBeNull()
  })

  it('a failed provider sign-in lands on the login page with the reason', async () => {
    route({ status: 401 })
    globalThis.location.hash = '#/login?error=denied'
    render(App)
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Sign-in was cancelled.'))
  })
})
