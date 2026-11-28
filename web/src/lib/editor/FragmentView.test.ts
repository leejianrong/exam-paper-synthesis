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
    // an adopted stylesheet where the DOM has them (jsdom since 31), else a <style> element
    const root = screen.getByTestId('fragment').shadowRoot!
    const css =
      root.adoptedStyleSheets?.flatMap((s) => Array.from(s.cssRules, (r) => r.cssText)).join('') ||
      root.querySelector('style')?.textContent
    expect(css?.replace(/[\s;]/g, '')).toContain('.question{color:red}')
  })

  it('shows an error and no html when the render fails', async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 422, text: async () => 'invalid question' })
    render(FragmentView, { props: { question: makeBankQuestion() } })
    expect(await screen.findByRole('alert')).toHaveTextContent("Couldn't show this question.")
  })
})

describe('fragment fonts (EXA-130)', () => {
  it('installs the @font-face rules at document level, once (shadow roots ignore them)', async () => {
    const { installFontFaces } = await import('./fragments')
    document.querySelector('style[data-fragment-fonts]')?.remove()
    const css = '@font-face{font-family:KaTeX_Main;src:url(data:font/woff2;base64,AAAA) format("woff2")} .katex{color:red}'
    installFontFaces(css)
    installFontFaces(css)
    const styles = document.querySelectorAll('style[data-fragment-fonts]')
    expect(styles).toHaveLength(1)
    expect(styles[0].textContent).toContain('font-family:KaTeX_Main')
    expect(styles[0].textContent).not.toContain('.katex')
  })
})
