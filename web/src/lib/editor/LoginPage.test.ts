import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/svelte'
import LoginPage from './LoginPage.svelte'

const fetchMock = vi.fn()
beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => vi.unstubAllGlobals())

const providers = (list: Array<{ name: string; label: string }>) =>
  fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => ({ providers: list, dev: false }) })

describe('LoginPage', () => {
  it('offers only the providers the server has, as links to the server login route', async () => {
    providers([
      { name: 'google', label: 'Google' },
      { name: 'github', label: 'GitHub' },
    ])
    render(LoginPage)
    const google = await screen.findByRole('link', { name: 'Continue with Google' })
    expect(google.getAttribute('href')).toMatch(/\/auth\/google\/login$/)
    expect(screen.getByRole('link', { name: 'Continue with GitHub' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Microsoft/ })).toBeNull()
  })

  it('says so when no provider is configured', async () => {
    providers([])
    render(LoginPage)
    expect(await screen.findByText(/not set up on this server/)).toBeInTheDocument()
  })

  it('says so when the server cannot be reached', async () => {
    fetchMock.mockRejectedValue(new Error('down'))
    render(LoginPage)
    expect(await screen.findByRole('alert')).toHaveTextContent('Cannot reach the server')
  })

  it('explains a failed or cancelled sign-in', async () => {
    providers([{ name: 'google', label: 'Google' }])
    render(LoginPage, { props: { error: 'denied' } })
    expect(screen.getByRole('alert')).toHaveTextContent('Sign-in was cancelled.')
    await screen.findByRole('link', { name: /Google/ })
  })
})
