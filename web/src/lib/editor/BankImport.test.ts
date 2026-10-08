import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte'
import BankImport from './BankImport.svelte'

const fetchMock = vi.fn()
beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => vi.unstubAllGlobals())

const reply = (results: Array<Record<string, unknown>>) => {
  const count = (s: string) => results.filter((r) => r.status === s).length
  return {
    ok: true,
    status: 200,
    json: async () => ({
      results,
      imported: count('imported'),
      replaced: count('replaced'),
      duplicate: count('duplicate'),
      invalid: count('invalid'),
    }),
  }
}
const sent = (n = 0) => JSON.parse(fetchMock.mock.calls[n][1].body)
const file = (name: string, body: unknown) =>
  new File([typeof body === 'string' ? body : JSON.stringify(body)], name, { type: 'application/json' })
const choose = (files: File[]) =>
  fireEvent.change(screen.getByLabelText('Choose JSON files'), { target: { files } })

describe('BankImport', () => {
  it('is disabled until there is something to import', async () => {
    render(BankImport)
    const go = screen.getByRole('button', { name: 'Import' })
    expect(go).toBeDisabled()
    await fireEvent.input(screen.getByLabelText('Paste JSON'), { target: { value: '{}' } })
    expect(go).toBeEnabled()
  })

  it('flattens files (an object, an array) and pasted JSON into one request', async () => {
    fetchMock.mockResolvedValue(
      reply([0, 1, 2, 3].map((index) => ({ index, id: `q${index}`, status: 'imported' }))),
    )
    const done = vi.fn()
    render(BankImport, { events: { done } })
    await choose([file('one.json', { id: 'a' }), file('many.json', [{ id: 'b' }, { id: 'c' }])])
    await fireEvent.input(screen.getByLabelText('Paste JSON'), { target: { value: '{"id":"d"}' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Import' }))

    await waitFor(() => expect(screen.getByRole('list', { name: 'Import results' })).toBeInTheDocument())
    expect(sent()).toEqual({ objects: [{ id: 'a' }, { id: 'b' }, { id: 'c' }, { id: 'd' }], replace: false })
    const items = screen.getAllByRole('listitem').filter((li) => li.classList.contains('row'))
    expect(items.map((li) => li.dataset.status)).toEqual(['imported', 'imported', 'imported', 'imported'])
    expect(items[1]).toHaveTextContent('many.json #1')
    expect(done.mock.calls[0][0].detail).toEqual({ imported: 4 })
  })

  it('sends the Replace flag', async () => {
    fetchMock.mockResolvedValue(reply([{ index: 0, id: 'a', status: 'replaced' }]))
    render(BankImport)
    await fireEvent.input(screen.getByLabelText('Paste JSON'), { target: { value: '{"id":"a"}' } })
    await fireEvent.click(screen.getByLabelText(/Replace existing/))
    await fireEvent.click(screen.getByRole('button', { name: 'Import' }))
    await waitFor(() => expect(sent().replace).toBe(true))
    expect(await screen.findByText('Replaced')).toBeInTheDocument()
  })

  it('shows each outcome, with path-pointed errors for the invalid ones', async () => {
    fetchMock.mockResolvedValue(
      reply([
        { index: 0, id: 'a', status: 'imported' },
        { index: 1, id: 'b', status: 'duplicate', errors: ['a question with this id is already in your bank'] },
        { index: 2, id: 'c', status: 'invalid', errors: ['question/total_marks: is a required property'] },
      ]),
    )
    const done = vi.fn()
    render(BankImport, { events: { done } })
    await fireEvent.input(screen.getByLabelText('Paste JSON'), { target: { value: '[{},{},{}]' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Import' }))
    expect(await screen.findByText('Already in your bank')).toBeInTheDocument()
    expect(screen.getByText('question/total_marks: is a required property')).toBeInTheDocument()
    expect(screen.getByText('Not imported')).toBeInTheDocument()
    expect(done).toHaveBeenCalledTimes(1) // something did import
  })

  it('reports unparseable JSON per source and still imports the rest', async () => {
    fetchMock.mockResolvedValue(reply([{ index: 0, id: 'ok', status: 'imported' }]))
    render(BankImport)
    await choose([file('broken.json', '{nope'), file('fine.json', { id: 'ok' })])
    await fireEvent.click(screen.getByRole('button', { name: 'Import' }))
    expect(await screen.findByText(/not valid JSON/)).toBeInTheDocument()
    expect(screen.getByText(/broken\.json/)).toBeInTheDocument()
    expect(sent().objects).toEqual([{ id: 'ok' }])
  })

  it('batches more than 200 questions', async () => {
    fetchMock.mockImplementation(async (_u: string, init: RequestInit) => {
      const n = JSON.parse(String(init.body)).objects.length
      return reply(Array.from({ length: n }, (_, index) => ({ index, id: `q${index}`, status: 'imported' })))
    })
    render(BankImport)
    const many = Array.from({ length: 450 }, (_, i) => ({ id: `q${i}` }))
    await choose([file('big.json', many)])
    await fireEvent.click(screen.getByRole('button', { name: 'Import' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3))
    expect([0, 1, 2].map((i) => sent(i).objects.length)).toEqual([200, 200, 50])
  })

  it('shows a server failure and does not claim success', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 413,
      statusText: 'Too Large',
      json: async () => ({ detail: 'import is larger than 2 MB' }),
    })
    const done = vi.fn()
    render(BankImport, { events: { done } })
    await fireEvent.input(screen.getByLabelText('Paste JSON'), { target: { value: '{}' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Import' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Import failed: import is larger than 2 MB')
    expect(done).not.toHaveBeenCalled()
  })
})
