import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte'
import MathPopover from './MathPopover.svelte'
import { closeMathEditor, openMathEditor } from './mathEditor'
import { routeFetch } from './fixtures'

// KaTeX is a global the page loads from /render/katex.js. Stub fetch so the loader runs,
// and install a stand-in whose render() throws for a known-bad formula.
const katexRender = vi.fn((latex: string, el: HTMLElement) => {
  if (latex.includes('\\bad')) throw new Error('KaTeX parse error: Undefined control sequence: \\bad')
  el.textContent = `typeset:${latex}`
})

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockImplementation(routeFetch({ '/render/question.css': '.q{}', '/render/katex.js': '' })))
  vi.stubGlobal('katex', { render: katexRender })
  katexRender.mockClear()
})
afterEach(() => {
  closeMathEditor()
  vi.unstubAllGlobals()
})

const open = (latex = '', apply = vi.fn()) => {
  openMathEditor({ latex, apply })
  return apply
}

describe('MathPopover', () => {
  it('is closed until a node asks for it', async () => {
    render(MathPopover)
    expect(screen.queryByRole('dialog', { name: 'Equation' })).not.toBeInTheDocument()
    open('x')
    expect(await screen.findByRole('dialog', { name: 'Equation' })).toBeInTheDocument()
    expect(screen.getByLabelText('LaTeX')).toHaveValue('x')
  })

  it('previews the formula live as you type', async () => {
    render(MathPopover)
    open()
    const field = await screen.findByLabelText('LaTeX')
    await fireEvent.input(field, { target: { value: '\\frac{1}{2}' } })
    await waitFor(() =>
      expect(document.querySelector('.preview .math-host')!.shadowRoot!.textContent).toContain(
        'typeset:\\frac{1}{2}',
      ),
    )
  })

  it('inserts the one-click snippets at the caret', async () => {
    render(MathPopover)
    open('a')
    await screen.findByRole('dialog')
    await fireEvent.click(screen.getByRole('button', { name: 'Fraction' }))
    expect(screen.getByLabelText('LaTeX')).toHaveValue('a\\frac{3}{4}')
    expect(screen.getAllByRole('button', { name: /Mixed number|Ratio|Percent|Multiply|Divide|Square|Pi/ })).toHaveLength(7)
  })

  it('Apply hands back the trimmed LaTeX and closes', async () => {
    render(MathPopover)
    const apply = open('x')
    await screen.findByRole('dialog')
    await fireEvent.input(screen.getByLabelText('LaTeX'), { target: { value: '  2 \\times 3  ' } })
    await waitFor(() => expect(screen.getByRole('button', { name: 'Apply' })).toBeEnabled())
    await fireEvent.click(screen.getByRole('button', { name: 'Apply' }))
    expect(apply).toHaveBeenCalledWith('2 \\times 3')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('shows a bad formula as an error and will not apply it', async () => {
    render(MathPopover)
    const apply = open('x')
    await screen.findByRole('dialog')
    await fireEvent.input(screen.getByLabelText('LaTeX'), { target: { value: '\\bad{1}' } })
    expect(await screen.findByRole('alert')).toHaveTextContent('Undefined control sequence')
    expect(screen.getByRole('button', { name: 'Apply' })).toBeDisabled()
    expect(apply).not.toHaveBeenCalled()
  })

  it('refuses LaTeX delimiters and an empty formula', async () => {
    render(MathPopover)
    open('x')
    await screen.findByRole('dialog')
    await fireEvent.input(screen.getByLabelText('LaTeX'), { target: { value: 'a \\) b' } })
    expect(await screen.findByRole('alert')).toHaveTextContent('Leave out')
    expect(screen.getByRole('button', { name: 'Apply' })).toBeDisabled()
    await fireEvent.input(screen.getByLabelText('LaTeX'), { target: { value: '   ' } })
    expect(screen.getByRole('button', { name: 'Apply' })).toBeDisabled()
  })

  it('Remove asks the node to delete the formula; Escape and Cancel just close', async () => {
    render(MathPopover)
    const apply = open('x')
    await screen.findByRole('dialog')
    await fireEvent.click(screen.getByRole('button', { name: 'Remove' }))
    expect(apply).toHaveBeenCalledWith(null)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    const again = open('y')
    await screen.findByRole('dialog')
    await fireEvent.keyDown(window, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    open('z')
    await fireEvent.click(await screen.findByRole('button', { name: 'Cancel' }))
    expect(again).not.toHaveBeenCalled()
  })
})
