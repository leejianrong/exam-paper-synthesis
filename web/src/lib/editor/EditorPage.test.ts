import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte'
import EditorPage from './EditorPage.svelte'
import { freeformDocNode, makeQuestion } from './fixtures'
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

  describe('free-form questions (W2a)', () => {
    const load = async (content: unknown[]) => {
      fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => record(content) })
      render(EditorPage, { props: { id: 'd1' } })
      await waitFor(() => expect(screen.getByLabelText('Paper title')).toHaveValue('Ratio Review'))
    }

    it('shows the typed body, the [marks] as printed, and a numbered answer entry', async () => {
      await load([
        questionNode(makeQuestion({ id: 'a' }, 'First.')),
        freeformDocNode({ marks: 4, body: 'Typed on the page.', answer: 'Written answer' }),
      ])
      const block = await waitFor(() => {
        const b = document.querySelector('.ffblock') as HTMLElement
        expect(b).toBeTruthy()
        return b
      })
      expect(block).toHaveTextContent('Typed on the page.')
      expect(block.querySelector('.ff-marks')).toHaveTextContent('[4]')
      expect(screen.getByText('7 marks', { selector: '.total' })).toBeInTheDocument()
      expect(document.querySelectorAll('.entry')).toHaveLength(2)
      expect(screen.getByRole('button', { name: 'Answer key PDF' })).toBeEnabled()
      expect(document.querySelector('.entry.freeform .ProseMirror')).toHaveTextContent('Written answer')
    })

    it('the marks field updates the page bracket and the total', async () => {
      await load([freeformDocNode({ marks: 2 })])
      const input = (await screen.findByLabelText('Marks')) as HTMLInputElement
      input.value = '5'
      await fireEvent.change(input)
      await waitFor(() => expect(screen.getByText('5 marks', { selector: '.total' })).toBeInTheDocument())
      expect(document.querySelector('.ff-marks')).toHaveTextContent('[5]')
      input.value = ''
      await fireEvent.change(input)
      await waitFor(() => expect(screen.getByText('0 marks', { selector: '.total' })).toBeInTheDocument())
      expect(document.querySelector('.ff-marks')).toHaveTextContent('')
    })

    it('"Add question → Free-form" inserts an empty block', async () => {
      await load([])
      await fireEvent.click(screen.getByRole('button', { name: 'Add question' }))
      await fireEvent.click(screen.getByRole('tab', { name: 'Free-form' }))
      await waitFor(() => expect(document.querySelectorAll('.ffblock')).toHaveLength(1))
      expect(screen.queryByRole('dialog', { name: 'Add question' })).not.toBeInTheDocument()
      expect(document.querySelectorAll('.entry.freeform')).toHaveLength(1)
    })

    it('an answer typed in the key is written back to the question node and saved', async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true })
      try {
        await load([freeformDocNode({ id: 'ff_w', marks: 1 })])
        const pm = (await waitFor(() => {
          const p = document.querySelector('.entry.freeform .ProseMirror')
          expect(p).toBeTruthy()
          return p
        })) as HTMLElement & { editor: import('@tiptap/core').Editor }
        pm.editor.commands.setContent('<p>Final answer</p>')
        await vi.advanceTimersByTimeAsync(1500)
        const put = fetchMock.mock.calls.find((c) => c[1]?.method === 'PUT')
        expect(put).toBeTruthy()
        const saved = JSON.parse(put![1].body).document.content.content[0]
        expect(saved.type).toBe('freeformQuestion')
        expect(JSON.stringify(saved.attrs.answer)).toContain('Final answer')
        expect(saved.attrs.block_id).toBe('ff_w')
      } finally {
        vi.useRealTimers()
      }
    })
  })
})
