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

describe('EditorPage images and equations (W2b)', () => {
  const load = async (content: unknown[]) => {
    fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
      if (String(url).endsWith('/assets') && init?.method === 'POST') {
        return {
          ok: true,
          status: 201,
          json: async () => ({ id: 'a'.repeat(32), mime: 'image/png', width: 2, height: 3, bytes: 9 }),
        }
      }
      return { ok: true, status: 200, json: async () => record(content), text: async () => '' }
    })
    render(EditorPage, { props: { id: 'd1' } })
    await waitFor(() => expect(screen.getByLabelText('Paper title')).toHaveValue('Ratio Review'))
  }

  it('the Image button uploads the chosen file and puts the figure on the page', async () => {
    await load([])
    const input = screen.getByLabelText('Choose image') as HTMLInputElement
    const file = new File(['png'], 'fig.png', { type: 'image/png' })
    await fireEvent.change(input, { target: { files: [file] } })
    await waitFor(() => expect(document.querySelector('.surface img.doc-image-img')).toBeTruthy())
    const post = fetchMock.mock.calls.find((c) => c[1]?.method === 'POST' && String(c[0]).endsWith('/assets'))!
    expect(post[1].headers['x-filename']).toBe('fig.png')
    expect(post[1].body).toBe(file)
  })

  it('says why when the server refuses the image, and puts nothing on the page', async () => {
    await load([])
    fetchMock.mockImplementation(async () => ({
      ok: false,
      status: 422,
      statusText: 'Unprocessable',
      json: async () => ({ detail: 'only PNG and JPEG images are accepted' }),
    }))
    const input = screen.getByLabelText('Choose image') as HTMLInputElement
    await fireEvent.change(input, { target: { files: [new File(['x'], 'a.gif', { type: 'image/gif' })] } })
    expect(await screen.findByRole('alert')).toHaveTextContent('only PNG and JPEG images are accepted')
    expect(document.querySelector('.surface img.doc-image-img')).toBeNull()
  })

  it('the Equation button opens the editor and Apply puts the formula inline', async () => {
    await load([{ type: 'paragraph', content: [{ type: 'text', text: 'Find ' }] }])
    await fireEvent.click(screen.getByRole('button', { name: 'Equation' }))
    const dialog = await screen.findByRole('dialog', { name: 'Equation' })
    await fireEvent.input(screen.getByLabelText('LaTeX'), { target: { value: '\\frac{3}{4}' } })
    await waitFor(() => expect(screen.getByRole('button', { name: 'Apply' })).toBeEnabled())
    await fireEvent.click(screen.getByRole('button', { name: 'Apply' }))
    expect(dialog).not.toBeInTheDocument()
    await waitFor(() => expect(document.querySelector('.surface .math-node')).toBeTruthy())
  })

  it('a saved paper with a figure and a formula in a free-form question loads and totals', async () => {
    const ff = freeformDocNode({ id: 'ff_m', marks: 2, body: 'See below.' })
    ff.content.push({ type: 'image', attrs: { asset_id: 'a'.repeat(32), alt: '', width_pct: 60 } } as never)
    ff.content[0].content!.push({ type: 'math', attrs: { latex: 'x^{2}' } } as never)
    await load([ff])
    await waitFor(() => expect(document.querySelector('.ffblock img.doc-image-img')).toBeTruthy())
    expect(document.querySelector('.ffblock .math-node')).toBeTruthy()
    expect(screen.getByText('2 marks', { selector: '.total' })).toBeInTheDocument()
    // the key entry shows the same figure read-only
    expect(document.querySelector('.entry.freeform .qtext img')).toBeTruthy()
  })
})

describe('EditorPage convert to free-form (W2c)', () => {
  const conversion = (dropped: string[] = []) => ({
    marks: 3,
    content: [
      { type: 'paragraph', content: [{ type: 'text', text: 'Converted question text.' }] },
      { type: 'image', attrs: { asset_id: 'a'.repeat(32), alt: 'Diagram', width_pct: 60 } },
    ],
    answer: {
      type: 'doc',
      content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Answer: $40' }] }],
    },
    dropped,
  })

  const load = async (convert: () => unknown) => {
    fetchMock.mockImplementation(async (url: string) => {
      if (String(url).endsWith('/convert/freeform')) return convert()
      return {
        ok: true,
        status: 200,
        json: async () => record([questionNode(makeQuestion({ id: 'a' }, 'Original generated text.'))]),
        text: async () => '',
      }
    })
    render(EditorPage, { props: { id: 'd1' } })
    await screen.findByText('Original generated text.')
  }

  it('replaces the generated block with an editable free-form one (marks, text, answer)', async () => {
    await load(() => ({ ok: true, status: 200, json: async () => conversion() }))
    await fireEvent.click(screen.getByRole('button', { name: 'Convert to free-form' }))

    await waitFor(() => expect(document.querySelector('.ffblock')).toBeTruthy())
    expect(screen.queryByTestId('question-block')).toBeNull()
    expect(document.querySelector('.ffblock')).toHaveTextContent('Converted question text.')
    expect(document.querySelector('.ffblock .ff-marks')).toHaveTextContent('[3]')
    expect(document.querySelector('.ffblock img.doc-image-img')).toBeTruthy()
    expect(document.querySelector('.entry.freeform .ProseMirror')).toHaveTextContent('Answer: $40')
    expect(screen.getByText('3 marks', { selector: '.total' })).toBeInTheDocument()
  })

  it('names the figures it had to drop', async () => {
    await load(() => ({ ok: true, status: 200, json: async () => conversion(['figure (could not be drawn)']) }))
    await fireEvent.click(screen.getByRole('button', { name: 'Convert to free-form' }))
    expect(await screen.findByText(/Not included: figure \(could not be drawn\)/)).toBeInTheDocument()
  })

  it('leaves the block alone and says why when the conversion fails', async () => {
    await load(() => ({ ok: false, status: 500, text: async () => 'boom' }))
    await fireEvent.click(screen.getByRole('button', { name: 'Convert to free-form' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('API 500')
    expect(screen.getByTestId('question-block')).toBeInTheDocument()
    expect(document.querySelector('.ffblock')).toBeNull()
  })

  it('undo restores the generated block', async () => {
    await load(() => ({ ok: true, status: 200, json: async () => conversion() }))
    await fireEvent.click(screen.getByRole('button', { name: 'Convert to free-form' }))
    await waitFor(() => expect(document.querySelector('.ffblock')).toBeTruthy())
    await fireEvent.click(screen.getByRole('button', { name: 'Undo' }))
    await waitFor(() => expect(screen.getByTestId('question-block')).toBeInTheDocument())
    expect(document.querySelector('.ffblock')).toBeNull()
    expect(screen.getByText('Original generated text.')).toBeInTheDocument()
  })
})

describe('EditorPage inspector (EXA-93)', () => {
  it('keeps status off the page and shows it in the inspector for the block you click', async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => record([questionNode(makeQuestion({ id: 'a' }, 'First.')), freeformDocNode({ id: 'ff_i' })]),
      text: async () => '',
    })
    render(EditorPage, { props: { id: 'd1' } })
    await screen.findByText('First.')
    const surface = document.querySelector('.surface') as HTMLElement
    expect(surface).not.toHaveTextContent(/engine-verified|From my bank|Unreviewed/)

    const inspector = screen.getByRole('complementary', { name: 'Inspector' })
    expect(inspector).toHaveTextContent('This paper')
    await fireEvent.click(screen.getByTestId('question-block'))
    expect(inspector).toHaveTextContent('Question 1')
    expect(inspector).toHaveTextContent('Engine-verified')
    await fireEvent.click(document.querySelector('.ffblock .ff-body') as HTMLElement)
    expect(inspector).toHaveTextContent('Question 2')
    expect(inspector).toHaveTextContent('not checked by the engine')
  })
})

describe('EditorPage export allowance (W3c)', () => {
  const setup = (exportReply: () => unknown) => {
    fetchMock.mockImplementation(async (url: string) => {
      if (String(url).endsWith('/auth/quota')) return { ok: true, status: 200, json: async () => ({ per_day: 30, left_day: 4 }) }
      if (String(url).includes('/export/')) return exportReply()
      return { ok: true, status: 200, json: async () => record([]), text: async () => '' }
    })
  }

  it('shows how many exports are left today', async () => {
    setup(() => ({ ok: true, status: 200, blob: async () => new Blob(['%PDF']) }))
    render(EditorPage, { props: { id: 'd1' } })
    expect(await screen.findByText('4 exports left today')).toBeInTheDocument()
  })

  it('a refused export (429) says when to try again instead of a raw API error', async () => {
    setup(() => ({
      ok: false,
      status: 429,
      json: async () => ({ detail: 'Export limit reached this minute. Try again in 42 seconds.' }),
    }))
    render(EditorPage, { props: { id: 'd1' } })
    await waitFor(() => expect(screen.getByLabelText('Paper title')).toHaveValue('Ratio Review'))
    await fireEvent.click(screen.getByRole('button', { name: 'Student PDF' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Try again in 42 seconds.')
    expect(screen.getByRole('alert')).not.toHaveTextContent('API 429')
  })
})
