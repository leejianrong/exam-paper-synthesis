import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/svelte'
import { get } from 'svelte/store'
import LoginPage from './LoginPage.svelte'
import { signInErrorText } from '../errors'
import { session } from '../session'

const fetchMock = vi.fn()
beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
  session.set({ status: 'anon' })
  vi.spyOn(console, 'warn').mockImplementation(() => {})
})
afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

const ok = (body: unknown) => ({ ok: true, status: 200, json: async () => body })
const providers = (list: Array<{ name: string; label: string }>, dev = false) =>
  fetchMock.mockResolvedValue(ok({ providers: list, dev }))

describe('LoginPage', () => {
  it('names the product and says what it is for', async () => {
    providers([])
    render(LoginPage)
    expect(screen.getByRole('heading', { level: 1, name: 'Exam papers' })).toBeInTheDocument()
    expect(screen.getByText(/maths papers with answer keys/)).toBeInTheDocument()
  })

  it("offers only the configured providers, in each provider's own wording", async () => {
    providers([
      { name: 'google', label: 'Google' },
      { name: 'github', label: 'GitHub' },
    ])
    render(LoginPage)
    const google = await screen.findByRole('link', { name: 'Sign in with Google' })
    expect(google.getAttribute('href')).toMatch(/\/auth\/google\/login$/)
    expect(google.querySelector('svg')).not.toBeNull()
    expect(screen.getByRole('link', { name: 'Sign in with GitHub' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Microsoft/ })).toBeNull()
    expect(screen.queryByText('Development only')).toBeNull()
  })

  it('says so when no provider is configured', async () => {
    providers([])
    render(LoginPage)
    expect(await screen.findByText("Sign-in isn't set up on this server yet.")).toBeInTheDocument()
  })

  it('says plainly when the server cannot be reached, and offers to try again', async () => {
    fetchMock.mockRejectedValueOnce(new Error('down'))
    render(LoginPage)
    expect(await screen.findByRole('alert')).toHaveTextContent(
      "Couldn't load the ways to sign in. Can't reach the server.",
    )
    providers([{ name: 'microsoft', label: 'Microsoft' }])
    await fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByRole('link', { name: 'Sign in with Microsoft' })).toBeInTheDocument()
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('Try again after an unanswered session check signs a teacher with a good cookie straight back in', async () => {
    session.set({ status: 'anon', unreachable: true })
    fetchMock.mockRejectedValueOnce(new Error('down')) // the providers, while the server restarts
    render(LoginPage)
    await screen.findByRole('alert')
    fetchMock.mockImplementation(async (url: string) =>
      String(url).endsWith('/auth/me')
        ? ok({ id: 'u1', email: null, name: 'Ann', dev: false })
        : ok({ providers: [{ name: 'google', label: 'Google' }], dev: false }),
    )
    await fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    await vi.waitFor(() => expect(get(session).status).toBe('user'))
    expect(fetchMock.mock.calls.map((c) => String(c[0]).replace(/^.*\/auth/, ''))).toEqual(['/providers', '/me'])
  })

  it('Try again when nobody is signed in reloads the providers only, and focuses the first button', async () => {
    session.set({ status: 'anon' })
    fetchMock.mockRejectedValueOnce(new Error('down'))
    render(LoginPage)
    await screen.findByRole('alert')
    providers([
      { name: 'google', label: 'Google' },
      { name: 'github', label: 'GitHub' },
    ])
    await fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    const google = await screen.findByRole('link', { name: 'Sign in with Google' })
    await vi.waitFor(() => expect(google).toHaveFocus())
    expect(fetchMock.mock.calls.some((c) => String(c[0]).endsWith('/auth/me'))).toBe(false)
  })

  it('explains a failed sign-in from the error code the API sends back', async () => {
    providers([{ name: 'google', label: 'Google' }])
    render(LoginPage, { props: { error: 'denied' } })
    expect(screen.getByRole('alert')).toHaveTextContent('Sign-in was cancelled.')
    await screen.findByRole('link', { name: /Google/ })
  })

  it('shows the dev stub only when the server has it on, marked as development only', async () => {
    providers([{ name: 'google', label: 'Google' }], true)
    render(LoginPage)
    expect(await screen.findByText('Development only')).toBeInTheDocument()
    fetchMock.mockResolvedValue(ok({ id: 'local', email: null, name: 'Local development', dev: true }))
    await fireEvent.click(screen.getByRole('button', { name: 'Continue without signing in' }))
    await vi.waitFor(() => expect(get(session).status).toBe('user'))
  })

  it('the dev button waits while it asks, and says so when the server still says no', async () => {
    providers([], true)
    render(LoginPage)
    const go = await screen.findByRole('button', { name: 'Continue without signing in' })
    let answer!: (v: unknown) => void
    fetchMock.mockReturnValueOnce(new Promise((r) => (answer = r)))
    await fireEvent.click(go)
    expect(screen.getByRole('button', { name: 'Continuing…' })).toBeDisabled()
    answer({ ok: false, status: 401, json: async () => ({}) })
    expect(await screen.findByRole('alert')).toHaveTextContent(
      "Couldn't continue. The server doesn't let you in without signing in any more.",
    )
    expect(screen.getByRole('button', { name: 'Continue without signing in' })).toBeEnabled()
    fetchMock.mockRejectedValueOnce(new Error('down'))
    await fireEvent.click(screen.getByRole('button', { name: 'Continue without signing in' }))
    await vi.waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent("Couldn't continue. Can't reach the server."))
  })

  it('with the dev stub and no provider, offers only the stub', async () => {
    providers([], true)
    render(LoginPage)
    expect(await screen.findByRole('button', { name: 'Continue without signing in' })).toBeInTheDocument()
    expect(screen.queryByText(/not set up/)).toBeNull()
  })
})

describe('signInErrorText', () => {
  it('words every code the API sends, without apologising', () => {
    for (const code of ['denied', 'state', 'provider', 'rate_limited', 'not_configured', 'other']) {
      const text = signInErrorText(code)
      expect(text).toMatch(/^[A-Z].*\.$/)
      expect(text).not.toMatch(/sorry|please|oops/i)
    }
    expect(signInErrorText('rate_limited')).toBe('Too many sign-in attempts. Try again in a few minutes.')
    expect(signInErrorText('constructor')).toBe("Sign-in didn't work. Try again.")
    expect(signInErrorText('')).toBe('')
  })
})
