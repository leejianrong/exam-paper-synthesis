import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/svelte'
import { makeBankQuestion, makeQuestion, routeFetch } from './fixtures'

import AddQuestion from './AddQuestion.svelte'

// The picker is exercised through the real api.ts with fetch stubbed. (Rejecting a
// vi.mock()ed api function the component handles is reported by Vitest 4 as an unhandled
// error; a failing HTTP response is not.)
const fetchMock = vi.fn()
beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => vi.unstubAllGlobals())

const ok = (body: unknown) => ({ ok: true, status: 200, json: async () => body })

describe('AddQuestion picker', () => {
  it('generates three candidates for the chosen topic and difficulty, then inserts one', async () => {
    const candidates = [1, 2, 3].map((n) => makeQuestion({ id: `c${n}` }, `Candidate ${n}.`))
    fetchMock.mockResolvedValue(ok({ questions: candidates }))
    const insert = vi.fn()
    render(AddQuestion, { props: {}, events: { insert } })

    await fireEvent.change(screen.getByLabelText('Topic'), { target: { value: 'speed' } })
    await fireEvent.change(screen.getByLabelText('Difficulty'), { target: { value: 'hard' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Generate' }))

    await waitFor(() => expect(screen.getAllByTestId('candidate')).toHaveLength(3))
    const body = JSON.parse(fetchMock.mock.calls[0][1].body)
    expect(body).toEqual({ blueprint_code: 'speed_hard', count: 3 })

    await fireEvent.click(screen.getAllByRole('button', { name: 'Use this' })[1])
    expect(insert.mock.calls[0][0].detail.question.id).toBe('c2')
  })

  it('shows an API error and keeps the dialog open', async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500, text: async () => 'down' })
    render(AddQuestion, { props: {} })
    await fireEvent.click(screen.getByRole('button', { name: 'Generate' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('API 500: down')
  })

  it('offers Free-form, and Escape closes', async () => {
    const close = vi.fn()
    render(AddQuestion, { props: {}, events: { close } })
    expect(screen.getByRole('tab', { name: 'From my bank' })).toBeEnabled()
    expect(screen.getByRole('tab', { name: 'Free-form' })).toBeEnabled()
    await fireEvent.keyDown(window, { key: 'Escape' })
    expect(close).toHaveBeenCalled()
  })

  describe('From my bank', () => {
    const item = (id: string, topic: string, reviewed: boolean) => ({
      id,
      topic,
      level: 'P6',
      difficulty: 'medium',
      source_type: 'sourced',
      reviewed,
      question: makeBankQuestion({ id }),
    })

    function stubBank(items: unknown[]) {
      fetchMock.mockImplementation(
        routeFetch({
          '/bank': { items },
          '/render/question.css': '.q{}',
          '/render/katex.js': '',
          '/render/question': { html: '<div class="frag">rendered</div>' },
        }),
      )
    }

    it('lists the owner\'s bank, filters by topic and review, and inserts a chosen question', async () => {
      stubBank([
        item('s1', 'Ratio', true),
        item('s2', 'Geometry', false),
        item('s3', 'Ratio', false),
      ])
      const insert = vi.fn()
      render(AddQuestion, { props: {}, events: { insert } })

      await fireEvent.click(screen.getByRole('tab', { name: 'From my bank' }))
      await waitFor(() => expect(screen.getAllByTestId('bank-item')).toHaveLength(3))
      expect(screen.getByRole('tab', { name: 'From my bank' })).toHaveAttribute('aria-selected', 'true')

      await fireEvent.change(screen.getByLabelText('Bank topic'), { target: { value: 'Ratio' } })
      expect(screen.getAllByTestId('bank-item')).toHaveLength(2)
      await fireEvent.click(screen.getByLabelText('Reviewed only'))
      expect(screen.getAllByTestId('bank-item')).toHaveLength(1)
      expect(screen.getByText('Reviewed')).toBeInTheDocument()

      await fireEvent.click(screen.getByRole('button', { name: 'Use this' }))
      expect(insert.mock.calls[0][0].detail.question.id).toBe('s1')
    })

    it('says how to fill an empty bank', async () => {
      stubBank([])
      render(AddQuestion, { props: {} })
      await fireEvent.click(screen.getByRole('tab', { name: 'From my bank' }))
      expect(await screen.findByText(/Nothing in your bank yet/)).toBeInTheDocument()
      expect(screen.getByText('mathgen bank import <file.json>')).toBeInTheDocument()
    })

    it('shows a bank error', async () => {
      fetchMock.mockResolvedValue({ ok: false, status: 401, text: async () => 'authentication required' })
      render(AddQuestion, { props: {} })
      await fireEvent.click(screen.getByRole('tab', { name: 'From my bank' }))
      expect(await screen.findByRole('alert')).toHaveTextContent('authentication required')
    })

    it('loads the bank once and keeps the templated tab usable', async () => {
      stubBank([item('s1', 'Ratio', true)])
      render(AddQuestion, { props: {} })
      await fireEvent.click(screen.getByRole('tab', { name: 'From my bank' }))
      await waitFor(() => expect(screen.getAllByTestId('bank-item')).toHaveLength(1))
      await fireEvent.click(screen.getByRole('tab', { name: 'Templated' }))
      expect(screen.getByRole('button', { name: 'Generate' })).toBeInTheDocument()
      await fireEvent.click(screen.getByRole('tab', { name: 'From my bank' }))
      expect(fetchMock.mock.calls.filter((c) => String(c[0]).endsWith('/bank'))).toHaveLength(1)
    })
  })

  it('Free-form inserts straight away, with no generation step', async () => {
    const freeform = vi.fn()
    render(AddQuestion, { props: {}, events: { freeform } })
    await fireEvent.click(screen.getByRole('tab', { name: 'Free-form' }))
    expect(freeform).toHaveBeenCalledTimes(1)
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('the bank tab opens the import screen, and importing refreshes the list', async () => {
    const item = (id: string) => ({
      id,
      topic: 'Ratio',
      level: 'P6',
      difficulty: 'standard',
      source_type: 'sourced',
      reviewed: false,
      question: makeBankQuestion({ id }),
    })
    let bank = [item('sourced:a')]
    fetchMock.mockImplementation(
      routeFetch({
        '/render/question.css': '.q{}',
        '/render/katex.js': '',
        '/render/question': { html: '<div class="frag">q</div>' },
        '/bank/import': () => {
          bank = [...bank, item('sourced:b')]
          return { results: [{ index: 0, id: 'sourced:b', status: 'imported' }], imported: 1, replaced: 0, duplicate: 0, invalid: 0 }
        },
        '/bank': () => ({ items: bank }),
      }),
    )
    render(AddQuestion, { props: {} })
    await fireEvent.click(screen.getByRole('tab', { name: 'From my bank' }))
    await waitFor(() => expect(screen.getAllByTestId('bank-item')).toHaveLength(1))

    await fireEvent.click(screen.getByRole('button', { name: 'Import…' }))
    expect(screen.getByRole('region', { name: 'Import questions' })).toBeInTheDocument()
    await fireEvent.input(screen.getByLabelText('Paste JSON'), { target: { value: '{"id":"sourced:b"}' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Import' }))
    await screen.findByText('Imported')
    await fireEvent.click(screen.getByRole('button', { name: 'Back to bank' }))
    await waitFor(() => expect(screen.getAllByTestId('bank-item')).toHaveLength(2))
  })
})
