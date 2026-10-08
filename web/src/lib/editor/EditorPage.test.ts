import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/svelte'
import EditorPage from './EditorPage.svelte'
import { makeQuestion } from './fixtures'
import { questionNode } from './templatedQuestion'

// Driven through the real docsApi with fetch stubbed.
const fetchMock = vi.fn()
beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => vi.unstubAllGlobals())

const record = (content: unknown[]) => ({
  id: 'd1',
  title: 'Ratio Review',
  total_marks: 6,
  version: 4,
  created_at: '2026-10-08T00:00:00Z',
  updated_at: '2026-10-08T00:00:00Z',
  document: {
    schema_version: '1.0.0',
    title: 'Ratio Review',
    content: { type: 'doc', content },
  },
})

describe('EditorPage', () => {
  it('loads a paper: title, question blocks, answer key and total marks', async () => {
    const q1 = makeQuestion({ id: 'a' }, 'First question text.')
    const q2 = makeQuestion({ id: 'b' }, 'Second question text.')
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => record([
        { type: 'heading', attrs: { level: 2 }, content: [{ type: 'text', text: 'Section A' }] },
        questionNode(q1),
        questionNode(q2),
      ]),
    })
    render(EditorPage, { props: { id: 'd1' } })

    await waitFor(() => expect(screen.getByLabelText('Paper title')).toHaveValue('Ratio Review'))
    expect(await screen.findByText('First question text.')).toBeInTheDocument()
    expect(screen.getByText('Second question text.')).toBeInTheDocument()
    expect(screen.getByText('Section A')).toBeInTheDocument()
    expect(screen.getAllByTestId('question-block')).toHaveLength(2)
    expect(document.querySelectorAll('.entry')).toHaveLength(2)
    expect(screen.getByText('6 marks', { selector: '.total' })).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Saved')
    expect(screen.getByRole('button', { name: 'Add question' })).toBeInTheDocument()
  })

  it('says so when the paper does not exist', async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 404, statusText: 'Not Found', json: async () => ({ detail: 'document not found' }) })
    render(EditorPage, { props: { id: 'nope' } })
    expect(await screen.findByText(/This paper was not found/)).toBeInTheDocument()
  })

  it('disables the answer-key export until there is a question', async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => record([]) })
    render(EditorPage, { props: { id: 'd1' } })
    await waitFor(() => expect(screen.getByLabelText('Paper title')).toHaveValue('Ratio Review'))
    expect(screen.getByRole('button', { name: 'Answer key PDF' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Student PDF' })).toBeEnabled()
  })
})
