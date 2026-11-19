import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createEvent, fireEvent, render, screen, waitFor, within } from '@testing-library/svelte'
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

/** Open the header's Export ▾ menu (EXA-160) and return the item with this name. */
async function exportItem(name: string) {
  if (!screen.queryByRole('menu', { name: 'Export' })) await fireEvent.click(screen.getByRole('button', { name: 'Export' }))
  return screen.getByRole('menuitem', { name })
}

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
    expect(screen.getByTestId('marks-total')).toHaveTextContent(/^\s*6 marks\s*$/)
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
    expect(await exportItem('Answer key (PDF)')).toHaveAttribute('aria-disabled', 'true')
    expect(await exportItem('Student paper (PDF)')).not.toHaveAttribute('aria-disabled')
  })

  it('the answer-key style switches between the school key and worked solutions', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    try {
      fetchMock.mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => record([questionNode(makeQuestion({ id: 'a' }, 'First.'))]),
      })
      render(EditorPage, { props: { id: 'd1' } })
      await waitFor(() => expect(screen.getByLabelText('Paper title')).toHaveValue('Ratio Review'))
      // a paper saved without key options keeps its worked solutions
      const style = screen.getByLabelText('Answer key style') as HTMLSelectElement
      expect(style.value).toBe('full')
      expect(style.selectedOptions[0].textContent).toBe('Worked solutions')
      expect(screen.getByLabelText('Answer key repeats each question')).toBeEnabled()
      expect(screen.queryByLabelText("Answer key shows each question's marks")).toBeNull()
      style.value = 'compact'
      await fireEvent.change(style)
      // the school key never repeats the question; its own options appear
      await waitFor(() => expect(screen.queryByLabelText('Answer key repeats each question')).toBeNull())
      expect(screen.getByLabelText("Answer key shows each question's marks")).not.toBeChecked()
      expect(screen.getByLabelText('Answer key shows the working for 1-mark questions')).toBeChecked()
      await fireEvent.click(screen.getByLabelText("Answer key shows each question's marks"))
      await vi.advanceTimersByTimeAsync(1500)
      const puts = fetchMock.mock.calls.filter((c) => c[1]?.method === 'PUT')
      expect(puts.length).toBeGreaterThan(0)
      expect(JSON.parse(puts.at(-1)![1].body).document.settings.key_options).toEqual({
        layout: 'compact',
        show_marks: true,
      })
    } finally {
      vi.useRealTimers()
    }
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
      expect(block.querySelector('.ff-area .marks')).toHaveTextContent('[4]')
      expect(screen.getByTestId('marks-total')).toHaveTextContent(/^\s*7 marks\s*$/)
      expect(document.querySelectorAll('.entry')).toHaveLength(2)
      expect(await exportItem('Answer key (PDF)')).not.toHaveAttribute('aria-disabled')
      expect(document.querySelector('.entry.freeform .ProseMirror')).toHaveTextContent('Written answer')
    })

    it('the marks field updates the page bracket and the total', async () => {
      await load([freeformDocNode({ marks: 2 })])
      const input = (await screen.findByLabelText('Marks')) as HTMLInputElement
      input.value = '5'
      await fireEvent.change(input)
      await waitFor(() => expect(screen.getByTestId('marks-total')).toHaveTextContent(/^\s*5 marks\s*$/))
      expect(document.querySelector('.ff-area .marks')).toHaveTextContent('[5]')
      input.value = ''
      await fireEvent.change(input)
      await waitFor(() => expect(screen.getByTestId('marks-total')).toHaveTextContent(/^\s*0 marks\s*$/))
      expect(document.querySelector('.ff-area .marks')).toBeNull()
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
    expect(screen.getByTestId('marks-total')).toHaveTextContent(/^\s*2 marks\s*$/)
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
    expect(document.querySelector('.ffblock .ff-area .marks')).toHaveTextContent('[3]')
    expect(document.querySelector('.ffblock img.doc-image-img')).toBeTruthy()
    expect(document.querySelector('.entry.freeform .ProseMirror')).toHaveTextContent('Answer: $40')
    expect(screen.getByTestId('marks-total')).toHaveTextContent(/^\s*3 marks\s*$/)
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

    const inspector = screen.getByRole('complementary', { name: 'Side panel' })
    expect(screen.getByRole('tab', { name: 'Paper' })).toHaveAttribute('aria-selected', 'true')
    expect(inspector).toHaveTextContent(/Questions\s*2/)
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
    await waitFor(() => expect(screen.getByLabelText('Paper title')).toHaveValue('Ratio Review'))
    await waitFor(async () => {
      await exportItem('Student paper (PDF)')
      expect(screen.getByText('4 exports left today')).toBeInTheDocument()
    })
  })

  it('a refused export (429) says when to try again instead of a raw API error', async () => {
    setup(() => ({
      ok: false,
      status: 429,
      json: async () => ({ detail: 'Export limit reached this minute. Try again in 42 seconds.' }),
    }))
    render(EditorPage, { props: { id: 'd1' } })
    await waitFor(() => expect(screen.getByLabelText('Paper title')).toHaveValue('Ratio Review'))
    await fireEvent.click(await exportItem('Student paper (PDF)'))
    expect(await screen.findByRole('alert')).toHaveTextContent('Try again in 42 seconds.')
    expect(screen.getByRole('alert')).not.toHaveTextContent('API 429')
  })
})

describe('EditorPage empty placeholders (EXA-137)', () => {
  const placeholder = (id: string) => ({
    type: 'freeformQuestion',
    attrs: { block_id: id, marks: 1, slot: { marks: 1, kind: 'mcq', placeholder: true } },
    content: [{ type: 'paragraph' }],
  })
  const refused = {
    ok: false,
    status: 409,
    json: async () => ({
      detail: { code: 'unfilled_placeholders', message: 'Questions 2, 3 are still empty.', questions: [2, 3] },
    }),
  }
  const exportUrls: string[] = []
  const setup = () => {
    exportUrls.length = 0
    fetchMock.mockImplementation(async (url: string) => {
      if (String(url).endsWith('/auth/quota')) return { ok: true, status: 200, json: async () => ({ per_day: 30, left_day: 4 }) }
      if (String(url).includes('/export/')) {
        exportUrls.push(String(url))
        return String(url).includes('allow_placeholders=true')
          ? { ok: true, status: 200, blob: async () => new Blob(['%PDF']) }
          : refused
      }
      const content = [freeformDocNode({ body: 'Q1', marks: 1 }), placeholder('p2'), placeholder('p3')]
      return { ok: true, status: 200, json: async () => record(content), text: async () => '' }
    })
  }

  it('a refused export lists the empty questions; Print anyway asks the server to print them', async () => {
    setup()
    vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: () => 'blob:x', revokeObjectURL: () => {} }))
    render(EditorPage, { props: { id: 'd1' } })
    expect(await screen.findByTestId('placeholders-left')).toHaveTextContent('2 placeholders to write')
    await fireEvent.click(await exportItem('Student paper (PDF)'))
    const dialog = await screen.findByRole('alertdialog', { name: '2 questions are still empty' })
    expect(dialog).toHaveTextContent('Questions 2 and 3')
    expect(exportUrls).toEqual([expect.stringMatching(/\/documents\/d1\/export\/student$/)])

    await fireEvent.click(within(dialog).getByRole('button', { name: 'Print anyway' }))
    await waitFor(() => expect(exportUrls).toHaveLength(2))
    expect(exportUrls[1]).toMatch(/\/export\/student\?allow_placeholders=true$/)
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('Fill them closes the warning and puts the caret in the first empty question', async () => {
    setup()
    const { container } = render(EditorPage, { props: { id: 'd1' } })
    await screen.findByTestId('placeholders-left')
    await fireEvent.click(await exportItem('Paper and key together (PDF)'))
    const dialog = await screen.findByRole('alertdialog')
    await fireEvent.click(within(dialog).getByRole('button', { name: 'Fill them' }))
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    expect(exportUrls).toHaveLength(1) // nothing printed
    const sel = window.getSelection()
    const blocks = container.querySelectorAll('.ffblock')
    expect(blocks).toHaveLength(3)
    expect(blocks[1].contains(sel?.anchorNode ?? null)).toBe(true)
  })

  it('Fill them finds the question by its printed number on a paper numbered from 16 (EXA-134)', async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (String(url).endsWith('/auth/quota')) return { ok: true, status: 200, json: async () => ({ per_day: 30, left_day: 4 }) }
      if (String(url).includes('/export/')) {
        return {
          ok: false,
          status: 409,
          json: async () => ({ detail: { code: 'unfilled_placeholders', message: 'Questions 17, 18 are still empty.', questions: [17, 18] } }),
        }
      }
      const content = [freeformDocNode({ body: 'Q16', marks: 1 }), placeholder('p2'), placeholder('p3')]
      const r = record(content)
      return {
        ok: true,
        status: 200,
        json: async () => ({ ...r, document: { ...r.document, settings: { number_from: 16 } } }),
        text: async () => '',
      }
    })
    const { container } = render(EditorPage, { props: { id: 'd1' } })
    await screen.findByTestId('placeholders-left')
    await fireEvent.click(await exportItem('Paper and key together (PDF)'))
    const dialog = await screen.findByRole('alertdialog')
    await fireEvent.click(within(dialog).getByRole('button', { name: 'Fill them' }))
    const sel = window.getSelection()
    const blocks = container.querySelectorAll('.ffblock')
    expect(blocks[1].contains(sel?.anchorNode ?? null)).toBe(true)
  })
})

describe('toolbar (P1)', () => {
  function renderEmpty() {
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => record([]),
    })
    return render(EditorPage, { props: { id: 'd1' } })
  }

  it('uses labelled icon buttons for lists, equation, image, undo and redo', async () => {
    renderEmpty()
    for (const name of [
      'Bulleted list',
      'Numbered list',
      'Equation',
      'Image',
      'Undo',
      'Redo',
    ]) {
      const b = await screen.findByRole('button', { name })
      expect(b.querySelector('svg')).not.toBeNull()
      expect(b).toHaveAttribute('title')
    }
  })

  it('is the second row of the sticky header, so it stays visible while scrolling', async () => {
    const { container } = renderEmpty()
    await screen.findByRole('toolbar', { name: 'Formatting' })
    expect(container.querySelector('header.ehead .tools')).not.toBeNull()
  })

  it('keeps cover page, blank page and page break in the ⋯ menu', async () => {
    renderEmpty()
    await fireEvent.click(await screen.findByRole('button', { name: 'More tools' }))
    const names = screen.getAllByRole('menuitem').map((m) => m.textContent?.trim())
    expect(names).toEqual(['Cover page', 'Blank page', 'Page break'])
  })

  it('says why Equation is unavailable instead of greying it out silently', async () => {
    renderEmpty()
    const eq = await screen.findByRole('button', { name: 'Equation' })
    await waitFor(() => expect(eq).toHaveAttribute('aria-disabled', 'true'))
    expect(eq.title).toMatch(/click into a line of text first/)
  })

  it('moves lists, equation and image into the ⋯ menu on a narrow window', async () => {
    const was = window.innerWidth
    window.innerWidth = 900
    try {
      renderEmpty()
      await screen.findByRole('toolbar', { name: 'Formatting' })
      expect(screen.queryByRole('button', { name: 'Bulleted list' })).toBeNull()
      await fireEvent.click(screen.getByRole('button', { name: 'More tools' }))
      const names = screen.getAllByRole('menuitem').map((m) => m.textContent?.trim())
      expect(names).toEqual(['Bulleted list', 'Numbered list', 'Equation', 'Image', 'Cover page', 'Blank page', 'Page break'])
    } finally {
      window.innerWidth = was
    }
  })
})

describe('paper layout (P2)', () => {
  function renderWith(settings?: object) {
    const q = makeQuestion({ id: 'a' }, 'Find x.')
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        ...record([questionNode(q), freeformDocNode({ marks: 2 })]),
        document: {
          schema_version: '1.4.0',
          title: 'Ratio Review',
          content: {
            type: 'doc',
            content: [questionNode(q), freeformDocNode({ marks: 2 })],
          },
          ...(settings ? { settings } : {}),
        },
      }),
    })
    return render(EditorPage, { props: { id: 'd1' } })
  }

  it('draws the working space and the Ans: line under every written question', async () => {
    renderWith()
    await screen.findByText('Find x.')
    await waitFor(() => expect(screen.getAllByTestId('answer-area')).toHaveLength(2))
    expect(screen.getByLabelText('Marks shown')).toHaveValue('answer')
  })

  it('moves the marks when the setting changes, and remembers a saved setting', async () => {
    renderWith({ marks_placement: 'question' })
    await screen.findByText('Find x.')
    const select = screen.getByLabelText('Marks shown') as HTMLSelectElement
    await waitFor(() => expect(select.value).toBe('question'))
    expect(document.querySelector('.ffblock .ff-marks')).toHaveTextContent('[2]')
    await fireEvent.change(select, { target: { value: 'answer' } })
    await waitFor(() => expect(document.querySelector('.ffblock .ff-marks')).toHaveTextContent(''))
    expect(document.querySelector('.ff-area .marks')).toHaveTextContent('[2]')
  })

  it('numbers the page and the key from a saved first question number (EXA-134)', async () => {
    renderWith({ number_from: 16 })
    await screen.findByText('Find x.')
    const field = screen.getByLabelText('First question number') as HTMLInputElement
    await waitFor(() => expect(field.value).toBe('16'))
    const surface = document.querySelector('.surface') as HTMLElement
    expect(surface.style.getPropertyValue('--q-start')).toBe('15')
    const nums = Array.from(document.querySelectorAll('.entry .n')).map((n) => n.textContent)
    expect(nums).toEqual(['16.', '17.'])
    await fireEvent.input(field, { target: { value: '' } })
    await waitFor(() => expect(surface.style.getPropertyValue('--q-start')).toBe('0'))
  })

  it('resizes a free-form block in place: the handle survives so a drag or key run continues', async () => {
    renderWith()
    await screen.findByText('Find x.')
    await waitFor(() => expect(document.querySelectorAll('.ffblock [role=slider]')).toHaveLength(1))
    const grip = document.querySelector('.ffblock [role=slider]') as HTMLElement
    grip.focus()
    await fireEvent.keyDown(grip, { key: 'ArrowDown' })
    await waitFor(() => expect(grip).toHaveAttribute('aria-valuenow', '55'))
    expect(grip.isConnected).toBe(true)
    expect(document.activeElement).toBe(grip)
    await fireEvent.keyDown(grip, { key: 'ArrowDown' })
    await waitFor(() => expect(grip).toHaveAttribute('aria-valuenow', '60'))
    expect(document.querySelector('.ffblock [role=slider]')).toBe(grip)
  })
})

describe('multi-part free-form questions (P3)', () => {
  function renderFreeform(content?: object[]) {
    const node = freeformDocNode({ id: 'ff_multi', marks: 2, body: 'A tank holds water.' })
    const doc = { ...node, ...(content ? { content } : {}) }
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        ...record([doc]),
        document: {
          schema_version: '1.5.0',
          title: 'Ratio Review',
          content: { type: 'doc', content: [doc] },
        },
      }),
    })
    return render(EditorPage, { props: { id: 'd1' } })
  }
  const para = (t: string) => ({ type: 'paragraph', content: [{ type: 'text', text: t }] })
  const part = (t: string, marks: number) => ({
    type: 'freeformPart',
    attrs: { marks, answer: { type: 'doc', content: [] } },
    content: [para(t)],
  })
  const labels = () =>
    Array.from(document.querySelectorAll('.ffp-label')).map((n) => n.textContent)

  it('adds lettered parts, each with its own marks and answer area; the total is their sum', async () => {
    renderFreeform()
    await waitFor(() => expect(document.querySelector('.ff-body')).not.toBeNull())
    const add = await screen.findByRole('button', { name: 'Add a lettered part' })
    await fireEvent.click(add)
    await fireEvent.click(add)
    await waitFor(() => expect(labels()).toEqual(['(a)', '(b)']))
    expect(document.querySelectorAll('.ffpart [data-testid=answer-area]')).toHaveLength(2)
    // The question's own marks and answer area give way to the parts'.
    expect(document.querySelector('.ffblock > .ff-main > .ff-area')).toHaveProperty('hidden', true)
    await waitFor(() => expect(screen.getByText('2 parts · 3 marks')).toBeInTheDocument())
    const inputs = screen.getAllByLabelText('Part marks') as HTMLInputElement[]
    inputs[0].value = '3'
    await fireEvent.change(inputs[0])
    await waitFor(() => expect(screen.getByTestId('marks-total')).toHaveTextContent(/^\s*4 marks\s*$/))
  })

  it('labels follow position: deleting (a) makes (b) the new (a)', async () => {
    renderFreeform([para('Stem.'), part('first', 1), part('second', 2)] as never)
    await waitFor(() => expect(labels()).toEqual(['(a)', '(b)']))
    const del = screen.getAllByRole('button', { name: 'Delete part' })[0]
    await fireEvent.click(del)
    await waitFor(() => expect(labels()).toEqual(['(a)']))
    const page = document.querySelector('.ff-body') as HTMLElement
    expect(page).toHaveTextContent('second')
    expect(page).not.toHaveTextContent('first')
  })

  it('the answer key has an entry per part, written back to that part', async () => {
    renderFreeform([para('Stem.'), part('first', 1), part('second', 2)] as never)
    await waitFor(() => expect(labels()).toEqual(['(a)', '(b)']))
    const key = screen.getByRole('region', { name: 'Answer key' })
    expect(key.querySelectorAll('.part')).toHaveLength(2)
    expect(key.querySelector('[data-part=b] .marks')).toHaveTextContent('[2]')
    expect(key.querySelectorAll('.entry.freeform > .head .marks')[0]).toHaveTextContent('[3]')
  })

  it('a question with no parts is exactly as before', async () => {
    renderFreeform()
    await waitFor(() => expect(document.querySelector('.ff-body')).not.toBeNull())
    expect(document.querySelectorAll('.ffpart')).toHaveLength(0)
    expect(screen.getByTestId('marks-total')).toHaveTextContent(/^\s*2 marks\s*$/)
  })
})

describe('opening a paper that starts with a block (cover / section)', () => {
  it('opens with a text cursor, not the first block selected (typing must never replace it)', async () => {
    const cover = { type: 'coverPage', attrs: { school: 'Pandan Primary', subject: 'Mathematics' } }
    const body = freeformDocNode({ id: 'ff_one', marks: 2, body: 'A tank holds water.' })
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        ...record([cover, body]),
        document: {
          schema_version: '1.10.0',
          title: 'Ratio Review',
          content: { type: 'doc', content: [cover, body] },
        },
      }),
    })
    render(EditorPage, { props: { id: 'd1' } })
    await waitFor(() => expect(document.querySelector('.cover-block')).not.toBeNull())
    expect(document.querySelector('.ProseMirror-selectednode')).toBeNull()
  })
})

describe('formatting toolbar focus (EXA-120)', () => {
  // jsdom never moves focus on mousedown, so do what a browser does: focus the button unless
  // the mousedown's default was prevented. Then the click runs the tool.
  const press = async (btn: HTMLElement) => {
    const down = createEvent.mouseDown(btn)
    fireEvent(btn, down)
    if (!down.defaultPrevented) btn.focus()
    await fireEvent.click(btn)
  }

  it('clicking a tool leaves the focus in the paper, so the next key types there', async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () =>
        record([{ type: 'paragraph', content: [{ type: 'text', text: 'Some words' }] }]),
    })
    render(EditorPage, { props: { id: 'd1' } })
    await waitFor(() => expect(document.querySelector('.page .ProseMirror')).not.toBeNull())
    const page = document.querySelector('.page .ProseMirror') as HTMLElement
    const toolbar = screen.getByRole('toolbar', { name: 'Formatting' })

    for (const name of ['Bold', 'Bulleted list', 'Undo']) {
      page.focus()
      await press(within(toolbar).getByRole('button', { name }))
      // At once, not a frame later: a key typed now must not reach (and re-press) the button.
      expect(page.contains(document.activeElement)).toBe(true)
    }
    // Keyboard users can still reach a tool.
    const bold = within(toolbar).getByRole('button', { name: 'Bold' })
    bold.focus()
    expect(document.activeElement).toBe(bold)
  })

  it('an insert from the ⋯ menu puts the caret back in the paper', async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => record([{ type: 'paragraph', content: [{ type: 'text', text: 'Some words' }] }]),
    })
    render(EditorPage, { props: { id: 'd1' } })
    await waitFor(() => expect(document.querySelector('.page .ProseMirror')).not.toBeNull())
    const page = document.querySelector('.page .ProseMirror') as HTMLElement
    page.focus()
    await fireEvent.click(screen.getByRole('button', { name: 'More tools' }))
    await fireEvent.click(screen.getByRole('menuitem', { name: 'Page break' }))
    expect(page.contains(document.activeElement)).toBe(true)
    expect(document.querySelector('.page-break-marker')).not.toBeNull()
  })
})
