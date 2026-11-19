import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createEvent, fireEvent, render, screen, waitFor, within } from '@testing-library/svelte'
import EditorPage from './EditorPage.svelte'
import { freeformDocNode, makeQuestion } from './fixtures'
import { questionNode } from './templatedQuestion'
import { chooseFromMenu, menuLabels, pillButton, selectBlock } from './blockTesting'

// Driven through the real docsApi with fetch stubbed.
const fetchMock = vi.fn()
beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => vi.unstubAllGlobals())

/** "Edit answer…" from an own question's ⋯ menu (EXA-162): the dialog, its editor made. */
async function openAnswer(block: Element, n: number): Promise<HTMLElement> {
  await chooseFromMenu(block, 'Edit answer…')
  const dialog = await screen.findByRole('dialog', { name: `Answer to question ${n}` })
  await waitFor(() => expect(dialog.querySelector('.ProseMirror')).not.toBeNull())
  return dialog
}

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
  it('loads a paper: title, question blocks and total marks', async () => {
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
    // the answer key is a view of its own, not loaded until it is shown (EXA-162)
    expect(screen.getByRole('button', { name: 'Paper' })).toHaveAttribute('aria-pressed', 'true')
    expect(fetchMock.mock.calls.some(([u]) => /\/preview\//.test(String(u)))).toBe(false)
    expect(screen.getByTestId('marks-total')).toHaveTextContent(/^\s*6 marks\s*$/)
    expect(screen.getByRole('status')).toHaveTextContent('Saved')
    expect(screen.getByRole('button', { name: 'Add question' })).toBeInTheDocument()
  })

  it('deleting a question offers Undo instead of a confirmation (EXA-161)', async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => record([questionNode(makeQuestion({ id: 'a' }, 'Keep me.')), questionNode(makeQuestion({ id: 'b' }, 'Delete me.'))]),
    })
    render(EditorPage, { props: { id: 'd1' } })
    const doomed = (await screen.findByText('Delete me.')).closest('.qblock') as HTMLElement
    doomed.focus()
    await fireEvent.keyDown(doomed, { key: 'Delete' })
    await waitFor(() => expect(screen.queryByText('Delete me.')).toBeNull())
    expect(screen.queryByRole('alertdialog')).toBeNull()
    const toast = screen.getByText(/Question deleted/).closest('[role="status"]') as HTMLElement
    expect(toast).toHaveTextContent('Question deleted · Undo')
    expect(screen.getByTestId('marks-total')).toHaveTextContent(/^\s*3 marks\s*$/)
    await fireEvent.click(within(toast).getByRole('button', { name: 'Undo' }))
    expect(await screen.findByText('Delete me.')).toBeInTheDocument()
    expect(screen.getAllByTestId('question-block')).toHaveLength(2)
    expect(screen.queryByText(/Question deleted/)).toBeNull()
  })

  it("the toast's Undo is only for that deletion: a later change closes it (review)", async () => {
    const gen = (id: string, text: string) => {
      const n = questionNode(makeQuestion({ id }, text))
      return { ...n, attrs: { ...n.attrs, block_id: id } }
    }
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => record([gen('a', 'Keep me.'), gen('b', 'Delete me.')]),
    })
    render(EditorPage, { props: { id: 'd1' } })
    const doomed = (await screen.findByText('Delete me.')).closest('.qblock') as HTMLElement
    doomed.focus()
    await fireEvent.keyDown(doomed, { key: 'Delete' })
    await waitFor(() => expect(screen.queryByText('Delete me.')).toBeNull())
    expect(screen.getByText(/Question deleted/)).toBeInTheDocument()
    // lock the other question: Undo would now undo the lock, so the toast goes
    const keep = (screen.getByText('Keep me.')).closest('.qblock') as HTMLElement
    keep.focus()
    await fireEvent.keyDown(keep, { key: 'l' })
    await waitFor(() => expect(screen.queryByText(/Question deleted/)).toBeNull())
    expect(screen.queryByText('Delete me.')).toBeNull()
  })

  it('an undo with Ctrl+Z closes the toast (review)', async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => record([questionNode(makeQuestion({ id: 'a' }, 'Keep me.')), questionNode(makeQuestion({ id: 'b' }, 'Delete me.'))]),
    })
    render(EditorPage, { props: { id: 'd1' } })
    const doomed = (await screen.findByText('Delete me.')).closest('.qblock') as HTMLElement
    doomed.focus()
    await fireEvent.keyDown(doomed, { key: 'Delete' })
    await waitFor(() => expect(screen.getByText(/Question deleted/)).toBeInTheDocument())
    const pm = document.querySelector('.ProseMirror') as HTMLElement
    pm.focus()
    await fireEvent.keyDown(pm, { key: 'z', ctrlKey: true })
    expect(await screen.findByText('Delete me.')).toBeInTheDocument()
    await waitFor(() => expect(screen.queryByText(/Question deleted/)).toBeNull())
  })

  describe('load and save states (EXA-165)', () => {
    const refuse = (status: number, detail = 'boom') => ({ ok: false, status, statusText: '', json: async () => ({ detail }) })
    const ok = (content: unknown[] = []) => ({ ok: true, status: 200, json: async () => record(content) })
    /** fetch answers the paper's GET with `first()`, then (after a retry) with the paper. */
    const loadWith = (first: () => unknown) => {
      let gets = 0
      fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
        if (String(url).endsWith('/auth/quota')) return { ok: false, status: 404, json: async () => ({}) }
        if (/\/documents\/[^/]+$/.test(String(url)) && !init?.method) return gets++ === 0 ? first() : ok()
        return ok()
      })
    }

    const puts = () => fetchMock.mock.calls.filter(([, init]) => init?.method === 'PUT').length

    /** A paper that didn't open must never be saved over: not when the page shows, and not
     *  once the autosave debounce would have run (an empty editor saving would wipe it). */
    async function noSaveFromAFailedLoad() {
      expect(puts()).toBe(0)
      vi.useFakeTimers()
      try {
        await vi.advanceTimersByTimeAsync(5000)
      } finally {
        vi.useRealTimers()
      }
      expect(puts()).toBe(0)
    }

    it('shows a skeleton, not a live editor, while the paper loads', async () => {
      let answer: (v: unknown) => void = () => {}
      fetchMock.mockImplementation((url: string) =>
        String(url).endsWith('/auth/quota') ? Promise.resolve(ok()) : new Promise((r) => (answer = r)),
      )
      render(EditorPage, { props: { id: 'd1' } })
      expect(screen.getByTestId('editor-skeleton')).toHaveTextContent('Opening the paper…')
      expect(document.querySelector('.ehead')).toHaveClass('hidden')
      answer(ok())
      await waitFor(() => expect(screen.getByLabelText('Paper title')).toHaveValue('Ratio Review'))
      expect(screen.queryByTestId('editor-skeleton')).toBeNull()
      expect(document.querySelector('.ehead')).not.toHaveClass('hidden')
    })

    it('an unknown paper is a page of its own with the way back, not an empty "Saved" editor', async () => {
      loadWith(() => refuse(404, 'document not found'))
      render(EditorPage, { props: { id: 'nope' } })
      const page = await screen.findByTestId('paper-unavailable')
      expect(within(page).getByRole('heading')).toHaveTextContent("This paper doesn't exist or was deleted")
      expect(within(page).getByRole('link', { name: /Back to Your papers/ })).toHaveAttribute('href', '#/')
      expect(within(page).queryByRole('button', { name: 'Try again' })).toBeNull()
      expect(document.querySelector('.ehead')).toHaveClass('hidden')
      expect(document.querySelector('.desk')).toHaveClass('hidden')
      expect(page).not.toHaveTextContent('404')
    })

    it('a paper of another account says so (403)', async () => {
      loadWith(() => refuse(403, 'forbidden'))
      render(EditorPage, { props: { id: 'd1' } })
      expect(await screen.findByRole('heading', { name: "You don't have access to this paper" })).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: 'Try again' })).toBeNull()
    })

    it('a server failure offers Try again, which opens the paper', async () => {
      loadWith(() => refuse(500))
      render(EditorPage, { props: { id: 'd1' } })
      const page = await screen.findByTestId('paper-unavailable')
      expect(within(page).getByRole('heading')).toHaveTextContent("This paper couldn't be opened")
      expect(page).toHaveTextContent('Something went wrong on our side.')
      expect(page).not.toHaveTextContent('boom')
      await noSaveFromAFailedLoad()
      await fireEvent.click(within(page).getByRole('button', { name: 'Try again' }))
      await waitFor(() => expect(screen.getByLabelText('Paper title')).toHaveValue('Ratio Review'))
      expect(screen.queryByTestId('paper-unavailable')).toBeNull()
    })

    it("no connection says the server can't be reached, and Try again works once it can", async () => {
      loadWith(() => Promise.reject(new TypeError('Failed to fetch')))
      render(EditorPage, { props: { id: 'd1' } })
      expect(await screen.findByRole('heading', { name: "Can't reach the server" })).toBeInTheDocument()
      expect(screen.getByTestId('paper-unavailable')).not.toHaveTextContent('Failed to fetch')
      await noSaveFromAFailedLoad()
      await fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
      await waitFor(() => expect(screen.getByLabelText('Paper title')).toHaveValue('Ratio Review'))
    })

    it('a failed save says so in words and Try again saves it', async () => {
      let puts = 0
      fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
        if (init?.method === 'PUT') {
          puts += 1
          return puts === 1 ? refuse(503, 'database unavailable') : { ok: true, status: 200, json: async () => ({ ...record([]), version: 5 }) }
        }
        return ok()
      })
      render(EditorPage, { props: { id: 'd1' } })
      const titleBox = await screen.findByLabelText('Paper title')
      await waitFor(() => expect(titleBox).toHaveValue('Ratio Review'))
      await fireEvent.input(titleBox, { target: { value: 'Renamed' } })
      const alert = await screen.findByRole('alert', {}, { timeout: 3000 })
      expect(alert).toHaveTextContent("Your latest changes aren't saved. The server is busy.")
      expect(screen.getByText('Not saved')).toBeInTheDocument()
      await fireEvent.click(within(alert).getByRole('button', { name: 'Try again' }))
      await waitFor(() => expect(puts).toBe(2))
      await waitFor(() => expect(screen.queryByText('Not saved')).toBeNull())
      expect(screen.queryByRole('alert')).toBeNull()
    })

    it('a save the server refused (not a passing fault) offers no Try again', async () => {
      fetchMock.mockImplementation(async (_url: string, init?: RequestInit) =>
        init?.method === 'PUT' ? refuse(413, 'document is too large') : ok(),
      )
      render(EditorPage, { props: { id: 'd1' } })
      const titleBox = await screen.findByLabelText('Paper title')
      await waitFor(() => expect(titleBox).toHaveValue('Ratio Review'))
      await fireEvent.input(titleBox, { target: { value: 'Renamed' } })
      const alert = await screen.findByRole('alert', {}, { timeout: 3000 })
      expect(alert).toHaveTextContent("Your latest changes aren't saved. Document is too large.")
      expect(within(alert).queryByRole('button', { name: 'Try again' })).toBeNull()
    })

    it('a fault in the page itself is a plain sentence, never the raw script error', async () => {
      // a reply without a document: reading its title throws a TypeError
      loadWith(() => ({ ok: true, status: 200, json: async () => ({ id: 'd1', version: 1 }) }))
      render(EditorPage, { props: { id: 'd1' } })
      const page = await screen.findByTestId('paper-unavailable')
      expect(within(page).getByRole('heading')).toHaveTextContent("This paper couldn't be opened")
      expect(page).toHaveTextContent('Something unexpected went wrong while opening it.')
      expect(page).not.toHaveTextContent(/undefined|TypeError|reading/)
    })

    it('a retry after a load that failed part way starts one editor, not a second', async () => {
      // the first reply builds the autosaver, then the editor fails on content it can't read
      loadWith(() => ok([{ type: 'templatedQuestion', attrs: { block_id: 'x', question: null } }]))
      render(EditorPage, { props: { id: 'd1' } })
      const page = await screen.findByTestId('paper-unavailable')
      await fireEvent.click(within(page).getByRole('button', { name: 'Try again' }))
      await waitFor(() => expect(screen.getByLabelText('Paper title')).toHaveValue('Ratio Review'))
      expect(document.querySelectorAll('.surface .ProseMirror')).toHaveLength(1)
    })
  })

  it('disables the answer-key export until there is a question', async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => record([]) })
    render(EditorPage, { props: { id: 'd1' } })
    await waitFor(() => expect(screen.getByLabelText('Paper title')).toHaveValue('Ratio Review'))
    expect(await exportItem('Answer key (PDF)')).toHaveAttribute('aria-disabled', 'true')
    expect(await exportItem('Student paper (PDF)')).not.toHaveAttribute('aria-disabled')
  })

  it('the answer key view: its style and options sit above the printed key (EXA-162)', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    try {
      fetchMock.mockImplementation(async (url: string) =>
        /\/preview\/key$/.test(String(url))
          ? { ok: true, status: 200, text: async () => '<p>PRINTED-KEY</p>' }
          : { ok: true, status: 200, json: async () => record([questionNode(makeQuestion({ id: 'a' }, 'First.'))]) },
      )
      render(EditorPage, { props: { id: 'd1' } })
      await waitFor(() => expect(screen.getByLabelText('Paper title')).toHaveValue('Ratio Review'))
      await fireEvent.click(screen.getByRole('button', { name: 'Answer key' }))
      const key = screen.getByRole('region', { name: 'Answer key' })
      // the server's own key, as it prints
      await waitFor(() => expect(key.querySelector('iframe')?.getAttribute('srcdoc')).toBe('<p>PRINTED-KEY</p>'))
      // a paper saved without key options keeps its worked solutions
      const styles = within(key).getByRole('radiogroup', { name: 'Answer key style' })
      expect(within(styles).getByRole('radio', { name: 'Worked solutions' })).toBeChecked()
      expect(within(key).getByRole('checkbox', { name: 'The question' })).toBeChecked()
      expect(within(key).queryByRole('checkbox', { name: 'Marks' })).toBeNull()
      await fireEvent.click(within(styles).getByRole('radio', { name: 'School key' }))
      // the school key never repeats the question; its own options appear, from its defaults
      await waitFor(() => expect(within(key).queryByRole('checkbox', { name: 'The question' })).toBeNull())
      expect(within(key).getByRole('checkbox', { name: 'Marking scheme (M1, A1)' })).not.toBeChecked()
      expect(within(key).getByRole('checkbox', { name: 'Working for 1-mark questions' })).not.toBeChecked()
      await fireEvent.click(within(key).getByRole('checkbox', { name: 'Marks' }))
      await vi.advanceTimersByTimeAsync(1500)
      const puts = fetchMock.mock.calls.filter((c) => c[1]?.method === 'PUT')
      expect(puts.length).toBeGreaterThan(0)
      expect(JSON.parse(puts.at(-1)![1].body).document.settings.key_options).toEqual({
        layout: 'compact',
        show_scheme: false,
        one_mark_working: false,
        show_marks: true,
      })
      // the options moved out of the side panel
      expect(screen.getByRole('complementary', { name: 'Side panel' })).not.toHaveTextContent('Answer key')
    } finally {
      vi.useRealTimers()
    }
  })

  it('"Leave out of answer key" from the ⋯ menu: the key view names it, redraws, and Include puts it back', async () => {
    let keys = 0
    fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
      if (/\/preview\/key$/.test(String(url))) return { ok: true, status: 200, text: async () => `<p>KEY ${++keys}</p>` }
      if (init?.method === 'PUT') return { ok: true, status: 200, json: async () => ({ ...record([]), version: 5 }) }
      return {
        ok: true,
        status: 200,
        json: async () => record([questionNode(makeQuestion({ id: 'a' }, 'First.')), questionNode(makeQuestion({ id: 'b' }, 'Second.'))]),
      }
    })
    render(EditorPage, { props: { id: 'd1' } })
    const second = (await screen.findByText('Second.')).closest('.qblock') as HTMLElement
    await chooseFromMenu(second, 'Leave out of answer key')
    await fireEvent.click(screen.getByRole('button', { name: 'Answer key' }))
    const key = screen.getByRole('region', { name: 'Answer key' })
    await waitFor(() => expect(key.querySelector('iframe')?.getAttribute('srcdoc')).toBe('<p>KEY 1</p>'))
    // the edit was saved before the key was asked for
    const put = fetchMock.mock.calls.findIndex((c) => c[1]?.method === 'PUT')
    const get = fetchMock.mock.calls.findIndex(([u]) => /\/preview\/key$/.test(String(u)))
    expect(put).toBeGreaterThan(-1)
    expect(put).toBeLessThan(get)
    expect(JSON.parse(fetchMock.mock.calls[put][1].body).document.content.content[1].attrs.in_key).toBe(false)
    await fireEvent.click(within(key).getByRole('button', { name: 'Include question 2 in the answer key' }))
    await waitFor(() => expect(within(key).queryByRole('button', { name: /Include question 2/ })).toBeNull())
    // the key redraws after the edit
    await waitFor(() => expect(key.querySelector('iframe')?.getAttribute('srcdoc')).toBe('<p>KEY 2</p>'), { timeout: 3000 })
    // and the question's menu offers to leave it out again
    await fireEvent.click(screen.getByRole('button', { name: 'Paper' }))
    expect(await menuLabels(second)).toContain('Leave out of answer key')
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
      expect(await exportItem('Answer key (PDF)')).not.toHaveAttribute('aria-disabled')
      await fireEvent.keyDown(screen.getByRole('menu', { name: 'Export' }), { key: 'Escape' })
      const dialog = await openAnswer(block, 2)
      expect(dialog.querySelector('.ProseMirror')).toHaveTextContent('Written answer')
    })

    it('the marks field updates the page bracket and the total', async () => {
      await load([freeformDocNode({ marks: 2 })])
      // the marks field sits in the question's pill (EXA-161), shown when it is selected
      await selectBlock(await waitFor(() => document.querySelector('.ffblock') as HTMLElement))
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
      await fireEvent.click(screen.getByRole('tab', { name: 'Write my own' }))
      await waitFor(() => expect(document.querySelectorAll('.ffblock')).toHaveLength(1))
      expect(screen.queryByRole('dialog', { name: 'Add question' })).not.toBeInTheDocument()
    })

    it('an answer written in Edit answer… is written back to the question node and saved', async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true })
      try {
        await load([freeformDocNode({ id: 'ff_w', marks: 1 })])
        const block = await waitFor(() => document.querySelector('.ffblock') as HTMLElement)
        const dialog = await openAnswer(block, 1)
        const pm = dialog.querySelector('.ProseMirror') as HTMLElement & { editor: import('@tiptap/core').Editor }
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
    expect(await screen.findByRole('alert')).toHaveTextContent("The image wasn't added. Only PNG and JPEG images are accepted.")
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
    // the answer dialog shows the same figure read-only, for reference
    const dialog = await openAnswer(document.querySelector('.ffblock') as HTMLElement, 1)
    expect(dialog.querySelector('.qtext img')).toBeTruthy()
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

  /** "Edit as my own text…" from the question's menu, then the confirmation (EXA-161). */
  const convert = async () => {
    await chooseFromMenu(screen.getByTestId('question-block'), 'Edit as my own text…')
    const dialog = await screen.findByRole('alertdialog', { name: 'Edit as your own text?' })
    expect(dialog).toHaveTextContent("won't be checked by the engine any more")
    await fireEvent.click(within(dialog).getByRole('button', { name: 'Edit as my own text' }))
  }

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
    await convert()

    await waitFor(() => expect(document.querySelector('.ffblock')).toBeTruthy())
    expect(screen.queryByTestId('question-block')).toBeNull()
    expect(document.querySelector('.ffblock')).toHaveTextContent('Converted question text.')
    expect(document.querySelector('.ffblock .ff-area .marks')).toHaveTextContent('[3]')
    expect(document.querySelector('.ffblock img.doc-image-img')).toBeTruthy()
    const dialog = await openAnswer(document.querySelector('.ffblock') as HTMLElement, 1)
    expect(dialog.querySelector('.ProseMirror')).toHaveTextContent('Answer: $40')
    expect(screen.getByTestId('marks-total')).toHaveTextContent(/^\s*3 marks\s*$/)
  })

  it('names the figures it had to drop', async () => {
    await load(() => ({ ok: true, status: 200, json: async () => conversion(['figure (could not be drawn)']) }))
    await convert()
    expect(await screen.findByText(/Not included: figure \(could not be drawn\)/)).toBeInTheDocument()
  })

  it('leaves the block alone and says why when the conversion fails', async () => {
    await load(() => ({ ok: false, status: 500, text: async () => 'boom' }))
    await convert()
    expect(await screen.findByRole('alert')).toHaveTextContent("The question wasn't changed. Something went wrong on our side.")
    expect(screen.getByTestId('question-block')).toBeInTheDocument()
    expect(document.querySelector('.ffblock')).toBeNull()
  })

  it('undo restores the generated block', async () => {
    await load(() => ({ ok: true, status: 200, json: async () => conversion() }))
    await convert()
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
    // the allowance is the reason: Try again is offered, and runs the export again
    const exports = () => fetchMock.mock.calls.filter(([u]) => String(u).includes('/export/')).length
    expect(exports()).toBe(1)
    await fireEvent.click(within(screen.getByRole('alert')).getByRole('button', { name: 'Try again' }))
    await waitFor(() => expect(exports()).toBe(2))
  })
})

describe('EditorPage action errors (EXA-165)', () => {
  it("an image error after a failed export doesn't keep the export's Try again", async () => {
    fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
      if (String(url).includes('/export/')) return { ok: false, status: 503, json: async () => ({ detail: 'export is busy' }) }
      if (String(url).endsWith('/assets') && init?.method === 'POST') {
        return { ok: false, status: 422, json: async () => ({ detail: 'only PNG and JPEG images are accepted' }) }
      }
      return { ok: true, status: 200, json: async () => record([]), text: async () => '' }
    })
    render(EditorPage, { props: { id: 'd1' } })
    await waitFor(() => expect(screen.getByLabelText('Paper title')).toHaveValue('Ratio Review'))
    await fireEvent.click(await exportItem('Student paper (PDF)'))
    const first = await screen.findByRole('alert')
    expect(first).toHaveTextContent("Couldn't export the PDF. The server is busy.")
    expect(within(first).getByRole('button', { name: 'Try again' })).toBeInTheDocument()

    const input = screen.getByLabelText('Choose image') as HTMLInputElement
    await fireEvent.change(input, { target: { files: [new File(['x'], 'a.gif', { type: 'image/gif' })] } })
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent("The image wasn't added."))
    expect(within(screen.getByRole('alert')).queryByRole('button', { name: 'Try again' })).toBeNull()
    expect(fetchMock.mock.calls.filter(([u]) => String(u).includes('/export/'))).toHaveLength(1)
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

  it('the header says how many placeholders are left; the link opens the Paper tab', async () => {
    setup()
    render(EditorPage, { props: { id: 'd1' } })
    const link = await screen.findByTestId('header-placeholders')
    expect(link).toHaveTextContent('2 placeholders to write')
    await fireEvent.click(screen.getByRole('tab', { name: /Question/ }))
    expect(screen.getByTestId('placeholders-left')).not.toBeVisible()
    await fireEvent.click(link)
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Paper' })).toHaveAttribute('aria-selected', 'true'))
    expect(screen.getByTestId('placeholders-left')).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Generated paper' })).toHaveFocus()
  })

  it('the link shows a hidden side panel first', async () => {
    localStorage.setItem('exam.editor.sidePanel', 'hidden')
    try {
      setup()
      render(EditorPage, { props: { id: 'd1' } })
      const link = await screen.findByTestId('header-placeholders')
      expect(screen.queryByRole('complementary', { name: 'Side panel' })).toBeNull()
      await fireEvent.click(link)
      await waitFor(() => expect(screen.getByRole('heading', { name: 'Generated paper' })).toHaveFocus())
      expect(screen.getByRole('complementary', { name: 'Side panel' })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: 'Paper' })).toHaveAttribute('aria-selected', 'true')
    } finally {
      localStorage.clear()
    }
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

  it('has no ⋯ on a wide window: the page inserts live in the Insert menu (EXA-163)', async () => {
    renderEmpty()
    await screen.findByRole('toolbar', { name: 'Formatting' })
    expect(screen.queryByRole('button', { name: 'More tools' })).toBeNull()
    expect(screen.getByRole('button', { name: 'Question' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Section' })).toBeInTheDocument()
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
      const menu = screen.getByRole('menu', { name: 'More tools' })
      const names = within(menu)
        .getAllByRole('menuitem')
        .map((m) => m.querySelector('.label')?.textContent)
      expect(names).toEqual(['Bulleted list', 'Numbered list', 'Equation', 'Image'])
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
    // the key view names the paper's own numbers
    expect(screen.getByRole('button', { name: /Edit the answer to question 17/ })).toBeInTheDocument()
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
    const ff = document.querySelector('.ffblock') as HTMLElement
    await fireEvent.click(await pillButton(ff, 'Part'))
    await fireEvent.click(await pillButton(ff, 'Part'))
    await waitFor(() => expect(labels()).toEqual(['(a)', '(b)']))
    expect(document.querySelectorAll('.ffpart [data-testid=answer-area]')).toHaveLength(2)
    // The question's own marks and answer area give way to the parts'.
    expect(document.querySelector('.ffblock > .ff-main > .ff-area')).toHaveProperty('hidden', true)
    await selectBlock(ff)
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

  it('Edit answer… has an answer per part, written back to that part', async () => {
    renderFreeform([para('Stem.'), part('first', 1), part('second', 2)] as never)
    await waitFor(() => expect(labels()).toEqual(['(a)', '(b)']))
    const dialog = await openAnswer(document.querySelector('.ffblock') as HTMLElement, 1)
    expect(dialog).toHaveTextContent('Stem.')
    await waitFor(() => expect(dialog.querySelectorAll('.ProseMirror')).toHaveLength(2))
    expect(within(dialog).getByRole('textbox', { name: 'Answer to question 1 part (a)' })).toBeInTheDocument()
    const b = within(dialog).getByRole('textbox', { name: 'Answer to question 1 part (b)' }) as HTMLElement & {
      editor: import('@tiptap/core').Editor
    }
    b.editor.commands.setContent('<p>PART-B</p>', { emitUpdate: true })
    const page = document.querySelector('.surface .ProseMirror') as HTMLElement & { editor: import('@tiptap/core').Editor }
    await waitFor(() => {
      const parts = JSON.stringify(page.editor.getJSON()).split('"type":"freeformPart"')
      expect(parts[2]).toContain('PART-B')
      expect(parts[1]).not.toContain('PART-B')
    })
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

  it('an insert from the Insert menu puts the caret back in the paper', async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => record([{ type: 'paragraph', content: [{ type: 'text', text: 'Some words' }] }]),
    })
    render(EditorPage, { props: { id: 'd1' } })
    await waitFor(() => expect(document.querySelector('.page .ProseMirror')).not.toBeNull())
    const page = document.querySelector('.page .ProseMirror') as HTMLElement
    page.focus()
    await fireEvent.click(screen.getByRole('menuitem', { name: 'Insert' }))
    await fireEvent.click(screen.getByRole('menuitem', { name: 'Page break' }))
    expect(page.contains(document.activeElement)).toBe(true)
    expect(document.querySelector('.page-break-marker')).not.toBeNull()
  })
})
