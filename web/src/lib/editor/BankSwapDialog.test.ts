import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/svelte'
import BankSwapDialog from './BankSwapDialog.svelte'
import { makeBankQuestion, makeQuestion, routeFetch } from './fixtures'

const fetchMock = vi.fn()
beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => vi.unstubAllGlobals())

const sourced = (id: string, topic: string, reviewed: boolean) => ({
  id,
  topic,
  level: 'P6',
  difficulty: 'medium',
  source_type: 'sourced',
  reviewed,
  question: makeBankQuestion({ id }),
})

function stub(items: unknown[]) {
  fetchMock.mockImplementation(
    routeFetch({
      '/swap/bank': { items },
      '/render/question.css': '.q{}',
      '/render/katex.js': '',
      '/render/question': { html: '<div class="frag">rendered</div>' },
    }),
  )
}

const open = (onPick = vi.fn(), onClose = vi.fn()) =>
  render(BankSwapDialog, { props: { docId: 'd1', blockId: 'blk-7', onPick, onClose } })

describe('Swap from your bank (EXA-33)', () => {
  it("asks the server for this place's fitting bank questions and shows topic, marks and review", async () => {
    const generated = { ...sourced('generated:g1', 'Volume', false), source_type: 'generated', question: makeQuestion({ id: 'generated:g1' }) }
    stub([sourced('sourced:example-1', 'Ratio', true), sourced('sourced:example-2', 'Ratio', false), generated])
    open()
    await waitFor(() => expect(screen.getAllByTestId('bank-swap-item')).toHaveLength(3))
    expect(String(fetchMock.mock.calls[0][0])).toContain('/documents/d1/swap/bank?block_id=blk-7')
    const [first, second, third] = screen.getAllByTestId('bank-swap-item')
    expect(first).toHaveTextContent('Ratio · P6')
    expect(first).toHaveTextContent('2 marks')
    expect(first).toHaveTextContent('Reviewed')
    expect(second).toHaveTextContent('Unreviewed')
    expect(third).toHaveTextContent('Generated') // proven by the engine: no review tag
  })

  it('picks a question with the keyboard-reachable Use this button', async () => {
    stub([sourced('sourced:example-1', 'Ratio', true), sourced('sourced:example-2', 'Speed', false)])
    const onPick = vi.fn()
    open(onPick)
    await waitFor(() => expect(screen.getAllByTestId('bank-swap-item')).toHaveLength(2))
    const use = screen.getByRole('button', { name: 'Use this Speed question' })
    use.focus()
    expect(document.activeElement).toBe(use)
    await fireEvent.click(use)
    expect(onPick.mock.calls[0][0].id).toBe('sourced:example-2')
  })

  it('says plainly when nothing in the bank fits', async () => {
    stub([])
    open()
    expect(await screen.findByTestId('bank-swap-empty')).toHaveTextContent('Nothing in your bank fits here')
    expect(screen.queryAllByTestId('bank-swap-item')).toHaveLength(0)
  })

  it('searches a longer list, and Escape closes it', async () => {
    stub(['a', 'b', 'c', 'd'].map((x, i) => sourced(`sourced:example-${x}`, i ? 'Ratio' : 'Volume', true)))
    const onClose = vi.fn()
    open(vi.fn(), onClose)
    await waitFor(() => expect(screen.getAllByTestId('bank-swap-item')).toHaveLength(4))
    const dialog = screen.getByRole('dialog', { name: 'Swap from your bank' })
    await fireEvent.input(within(dialog).getByLabelText('Search bank questions'), { target: { value: 'volume' } })
    expect(screen.getAllByTestId('bank-swap-item')).toHaveLength(1)
    await fireEvent.keyDown(dialog, { key: 'Escape' })
    expect(onClose).toHaveBeenCalled()
  })

  it('shows a failure with a way to try again', async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500, text: async () => 'down', json: async () => ({}) })
    open()
    expect(await screen.findByRole('button', { name: /try again/i })).toBeInTheDocument()
    expect(screen.queryByTestId('bank-swap-empty')).toBeNull()
  })
})
