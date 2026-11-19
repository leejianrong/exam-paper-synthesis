import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/svelte'
import BankPage from './BankPage.svelte'
import { makeBankQuestion, routeFetch } from './editor/fixtures'

// Through the real api.ts with fetch stubbed, as the add-question picker's tests do.
const fetchMock = vi.fn()
beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => vi.unstubAllGlobals())

const item = (id: string, over: Record<string, unknown> = {}) => ({
  id,
  topic: 'Ratio',
  level: 'P6',
  difficulty: 'medium',
  source_type: 'sourced',
  reviewed: false,
  question: makeBankQuestion({ id }),
  ...over,
})

const RENDER = {
  '/render/question.css': '.q{}',
  '/render/katex.js': '',
  '/render/question': { html: '<div class="frag">q</div>' },
}

function stub(routes: Record<string, unknown>) {
  fetchMock.mockImplementation(routeFetch({ ...RENDER, ...routes }))
}

const cards = () => screen.queryAllByTestId('bank-question')

describe('BankPage (EXA-167)', () => {
  it('shows a skeleton while the bank loads', async () => {
    fetchMock.mockReturnValue(new Promise(() => {}))
    render(BankPage)
    expect(screen.getByTestId('bank-skeleton')).toHaveTextContent('Loading your question bank…')
  })

  it('lists the bank and filters it by topic, level, difficulty, source, review and search', async () => {
    stub({
      '/bank': {
        items: [
          item('s1', { reviewed: true }),
          item('s2', { topic: 'Geometry', level: 'P5', difficulty: 'hard' }),
          item('s3', { difficulty: 'easy', question: makeBankQuestion({ id: 's3', question: { total_marks: 1, parts: [{ text: 'Find the area of the rectangle.', marks: 1 }] } }) }),
          item('g1', { source_type: 'generated', topic: 'Speed' }),
        ],
      },
    })
    render(BankPage)
    await waitFor(() => expect(cards()).toHaveLength(4))
    expect(screen.getByTestId('bank-count')).toHaveTextContent('4 questions')
    // an imported question shows its review state; a generated one says so, with no review control
    expect(within(cards()[0]).getByText('Reviewed')).toBeInTheDocument()
    expect(within(cards()[1]).getByText('Unreviewed')).toBeInTheDocument()
    expect(within(cards()[3]).getByText('Generated')).toBeInTheDocument()
    expect(within(cards()[3]).queryByRole('button', { name: /review/i })).toBeNull()

    await fireEvent.change(screen.getByLabelText('Topic'), { target: { value: 'Ratio' } })
    expect(cards()).toHaveLength(2)
    expect(screen.getByTestId('bank-count')).toHaveTextContent('2 of 4 questions')
    await fireEvent.change(screen.getByLabelText('Difficulty'), { target: { value: 'easy' } })
    expect(cards()).toHaveLength(1)
    await fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    expect(cards()).toHaveLength(4)

    await fireEvent.change(screen.getByLabelText('Level'), { target: { value: 'P5' } })
    expect(cards()).toHaveLength(1)
    await fireEvent.change(screen.getByLabelText('Level'), { target: { value: '' } })
    await fireEvent.change(screen.getByLabelText('Source'), { target: { value: 'generated' } })
    expect(cards()).toHaveLength(1)
    await fireEvent.change(screen.getByLabelText('Source'), { target: { value: '' } })
    await fireEvent.change(screen.getByLabelText('Review'), { target: { value: 'unreviewed' } })
    expect(cards()).toHaveLength(2)
    await fireEvent.change(screen.getByLabelText('Review'), { target: { value: '' } })

    await fireEvent.input(screen.getByLabelText('Search questions'), { target: { value: 'rectangle' } })
    expect(cards()).toHaveLength(1)
    await fireEvent.input(screen.getByLabelText('Search questions'), { target: { value: 'zebra' } })
    expect(screen.getByText('No questions match these filters.')).toBeInTheDocument()
    await fireEvent.keyDown(screen.getByLabelText('Search questions'), { key: 'Escape' })
    expect(cards()).toHaveLength(4)
  })

  it('marks a question reviewed only after the confirmation, and can withdraw it', async () => {
    const puts: unknown[] = []
    stub({
      '/review': (init?: RequestInit) => {
        puts.push(JSON.parse(String(init?.body)))
        return {}
      },
      '/bank': { items: [item('s1')] },
    })
    render(BankPage)
    await waitFor(() => expect(cards()).toHaveLength(1))
    await fireEvent.click(screen.getByRole('button', { name: 'Mark as reviewed…' }))
    const go = screen.getByRole('button', { name: 'Mark as reviewed' })
    expect(go).toBeDisabled()
    await fireEvent.click(screen.getByLabelText(/I have checked this question/))
    await fireEvent.click(go)
    await waitFor(() => expect(within(cards()[0]).getByText('Reviewed')).toBeInTheDocument())
    expect(puts).toEqual([{ reviewed: true }])

    await fireEvent.click(screen.getByRole('button', { name: 'Withdraw review' }))
    await waitFor(() => expect(within(cards()[0]).getByText('Unreviewed')).toBeInTheDocument())
    expect(puts).toEqual([{ reviewed: true }, { reviewed: false }])
  })

  it('imports from a file in a dialog, then lists what arrived', async () => {
    let bank = [item('s1')]
    stub({
      '/bank/import': () => {
        bank = [...bank, item('s2')]
        return { results: [{ index: 0, id: 's2', status: 'imported' }], imported: 1, replaced: 0, duplicate: 0, invalid: 0 }
      },
      '/bank': () => ({ items: bank }),
    })
    render(BankPage)
    await waitFor(() => expect(cards()).toHaveLength(1))

    await fireEvent.click(screen.getByRole('button', { name: 'Import questions from a file' }))
    const dialog = screen.getByRole('dialog', { name: 'Import questions from a file' })
    const file = new File([JSON.stringify({ id: 's2' })], 's2.json', { type: 'application/json' })
    await fireEvent.change(within(dialog).getByLabelText('Choose JSON files'), { target: { files: [file] } })
    await fireEvent.click(within(dialog).getByRole('button', { name: 'Import' }))
    await within(dialog).findByText('Imported')
    await waitFor(() => expect(cards()).toHaveLength(2))
    expect(screen.getByText('1 question imported.')).toBeInTheDocument()

    await fireEvent.click(within(dialog).getByRole('button', { name: 'Back to bank' }))
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('reports a duplicate and replaces it when asked', async () => {
    const sent: unknown[] = []
    stub({
      '/bank/import': (init?: RequestInit) => {
        const body = JSON.parse(String(init?.body))
        sent.push(body.replace)
        const status = body.replace ? 'replaced' : 'duplicate'
        return { results: [{ index: 0, id: 's1', status }], imported: 0, replaced: body.replace ? 1 : 0, duplicate: body.replace ? 0 : 1, invalid: 0 }
      },
      '/bank': { items: [item('s1')] },
    })
    render(BankPage)
    await waitFor(() => expect(cards()).toHaveLength(1))
    await fireEvent.click(screen.getByRole('button', { name: 'Import questions from a file' }))
    const dialog = screen.getByRole('dialog')
    await fireEvent.input(within(dialog).getByLabelText('Paste JSON'), { target: { value: '{"id":"s1"}' } })
    await fireEvent.click(within(dialog).getByRole('button', { name: 'Import' }))
    expect(await within(dialog).findByText('Already in your bank')).toBeInTheDocument()
    await fireEvent.click(within(dialog).getByLabelText(/Replace existing questions/))
    await fireEvent.click(within(dialog).getByRole('button', { name: 'Import' }))
    expect(await within(dialog).findByText('Replaced')).toBeInTheDocument()
    expect(sent).toEqual([false, true])
  })

  it('says what to do with an empty bank', async () => {
    stub({ '/bank': { items: [] } })
    render(BankPage)
    expect(await screen.findByText('Your bank is empty.')).toBeInTheDocument()
    expect(screen.queryByRole('search')).toBeNull()
    expect(screen.getByRole('button', { name: 'Import questions from a file' })).toBeInTheDocument()
  })

  it('says plainly when the bank does not load, and Try again loads it', async () => {
    let fail = true
    fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
      if (fail && String(url).endsWith('/bank')) return { ok: false, status: 503, json: async () => ({}), text: async () => '' }
      return routeFetch({ ...RENDER, '/bank': { items: [item('s1')] } })(url, init)
    })
    render(BankPage)
    expect(await screen.findByRole('alert')).toHaveTextContent("Couldn't load your question bank. The server is busy.")
    fail = false
    await fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    await waitFor(() => expect(cards()).toHaveLength(1))
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('offers no Try again when asking again will not help', async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 403, json: async () => ({}), text: async () => '' })
    render(BankPage)
    expect(await screen.findByRole('alert')).toHaveTextContent("Couldn't load your question bank.")
    expect(screen.queryByRole('button', { name: 'Try again' })).toBeNull()
  })

  it('draws a long bank twenty at a time', async () => {
    stub({ '/bank': { items: Array.from({ length: 25 }, (_, i) => item(`s${i}`)) } })
    render(BankPage)
    await waitFor(() => expect(cards()).toHaveLength(20))
    await fireEvent.click(screen.getByRole('button', { name: 'Show more (5 left)' }))
    expect(cards()).toHaveLength(25)
    expect(cards()[20]).toHaveFocus()
    expect(screen.queryByRole('button', { name: /Show more/ })).toBeNull()
  })
})
