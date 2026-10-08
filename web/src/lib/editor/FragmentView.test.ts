import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/svelte'
import FragmentView from './FragmentView.svelte'
import { makeBankQuestion, routeFetch } from './fixtures'

const fetchMock = vi.fn()
beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => vi.unstubAllGlobals())

const shadowText = () =>
  (screen.getByTestId('fragment').shadowRoot?.textContent ?? '').trim()

describe('FragmentView', () => {
  it('draws the engine-rendered html inside a shadow root, with the stylesheet', async () => {
    const calls: Array<{ mode: string; number: number | null }> = []
    fetchMock.mockImplementation(
      routeFetch({
        '/render/question.css': '.question{color:red}',
        '/render/katex.js': '/* katex */',
        '/render/question': (init?: RequestInit) => {
          const body = JSON.parse(String(init?.body))
          calls.push({ mode: body.mode, number: body.number })
          return { html: '<div class="frag"><section class="question">Pick (A) or (B)</section></div>' }
        },
      }),
    )
    render(FragmentView, { props: { question: makeBankQuestion(), mode: 'key', number: 3 } })

    await waitFor(() => expect(shadowText()).toContain('Pick (A) or (B)'))
    expect(calls).toEqual([{ mode: 'key', number: 3 }])
    // Isolated from the app: nothing leaked into the light DOM.
    expect(screen.queryByText('Pick (A) or (B)')).not.toBeInTheDocument()
    // jsdom has no adopted stylesheets, so the stylesheet falls back to a <style> element.
    const root = screen.getByTestId('fragment').shadowRoot!
    expect(root.querySelector('style')?.textContent).toContain('.question{color:red}')
  })

  it('shows an error and no html when the render fails', async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 422, text: async () => 'invalid question' })
    render(FragmentView, { props: { question: makeBankQuestion() } })
    expect(await screen.findByRole('alert')).toHaveTextContent('API 422')
  })
})
