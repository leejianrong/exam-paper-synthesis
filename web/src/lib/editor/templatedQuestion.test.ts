// The W1c spike, kept as a regression test: a Svelte 5 component lives inside a
// ProseMirror node view, survives node updates, reports edits back into the document,
// and is torn down on delete.
import { describe, it, expect, afterEach, vi } from 'vitest'
import { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { fireEvent, screen, waitFor } from '@testing-library/svelte'
import { TemplatedQuestion, questionNode } from './templatedQuestion'
import {
  makeBankQuestion,
  makeMultipartQuestion,
  makeQuestion,
  makeTableQuestion,
  routeFetch,
} from './fixtures'
import type { DocJSON } from './doc'
import { chooseFromMenu, menuLabels, pillButton, selectBlock } from './blockTesting'

let editor: Editor | null = null
afterEach(() => {
  editor?.destroy()
  editor = null
  vi.unstubAllGlobals()
})

function make(content: DocJSON, onAddBelow = vi.fn(), onNotice = vi.fn()) {
  const el = document.createElement('div')
  document.body.appendChild(el)
  editor = new Editor({
    element: el,
    extensions: [StarterKit, TemplatedQuestion.configure({ onAddBelow, onNotice })],
    content,
  })
  return { editor, el, onAddBelow }
}

const two = (): DocJSON => ({
  type: 'doc',
  content: [
    questionNode(makeQuestion({ id: 'a' }, 'First question text.')),
    questionNode(makeQuestion({ id: 'b' }, 'Second question text.')),
  ],
})

const texts = (e: Editor) =>
  (e.getJSON().content ?? [])
    .filter((n) => n.type === 'templatedQuestion')
    .map((n) => (n.attrs?.question as { id: string }).id)

describe('templatedQuestion node view', () => {
  it('mounts a Svelte component for each block', () => {
    make(two())
    expect(screen.getByText('First question text.')).toBeInTheDocument()
    expect(screen.getByText('Second question text.')).toBeInTheDocument()
    expect(screen.getAllByTestId('question-block')).toHaveLength(2)
  })

  it('shows a single-part question\'s data table in the block (EXA-148)', () => {
    make({ type: 'doc', content: [questionNode(makeTableQuestion())] })
    const table = screen.getByRole('table')
    expect(table).toHaveTextContent('Postage for letters')
    expect(table).toHaveTextContent('Mass of letter')
    expect(table).toHaveTextContent('Above 20 g, up to 40 g')
    expect(table).toHaveTextContent('$0.55')
  })

  it('round-trips block_id and the frozen snapshot through getJSON', () => {
    const doc = two()
    const { editor: e } = make(doc)
    const out = e.getJSON().content ?? []
    expect(out[0].attrs?.block_id).toBe(doc.content[0].attrs?.block_id)
    expect((out[1].attrs?.question as { id: string }).id).toBe('b')
  })

  it('removes the block (and unmounts its component) on Delete', async () => {
    const { editor: e } = make(two())
    await chooseFromMenu(screen.getAllByTestId('question-block')[0], 'Delete')
    await waitFor(() => expect(screen.queryByText('First question text.')).not.toBeInTheDocument())
    expect(texts(e)).toEqual(['b'])
  })

  it('moves a block down and up', async () => {
    const { editor: e } = make(two())
    await chooseFromMenu(screen.getAllByTestId('question-block')[0], 'Move down')
    await waitFor(() => expect(texts(e)).toEqual(['b', 'a']))
    await chooseFromMenu(screen.getAllByTestId('question-block')[1], 'Move up')
    await waitFor(() => expect(texts(e)).toEqual(['a', 'b']))
  })

  it('asks the page to open the picker after the block', async () => {
    const { onAddBelow } = make(two())
    await chooseFromMenu(screen.getAllByTestId('question-block')[0], 'Add question below')
    expect(onAddBelow).toHaveBeenCalledTimes(1)
    expect(onAddBelow.mock.calls[0][0]).toBeGreaterThan(0)
  })

  it('replaces the snapshot when an edit returns a child, updating the view in place', async () => {
    const child = makeQuestion({ id: 'a:v2' }, 'Regenerated question text.')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ question: child }) }),
    )
    const { editor: e } = make(two())
    await chooseFromMenu(screen.getAllByTestId('question-block')[0], 'Make easier')
    await waitFor(() => expect(screen.getByText('Regenerated question text.')).toBeInTheDocument())
    expect(texts(e)).toEqual(['a:v2', 'b'])
    expect(screen.queryByText('First question text.')).not.toBeInTheDocument()
  })

  it('Edit numbers… re-solves and locks the question in one undoable step (EXA-89)', async () => {
    const numbers = [{ key: 'total', label: 'Amount shared ($)', list: false, minimum: 12, maximum: 2000 }]
    const child = makeQuestion({ id: 'a:v2' }, 'Ann, Ben and Cal share $180 in the ratio 2 : 3 : 4.')
    vi.stubGlobal('fetch', routeFetch({ '/params': { slots: [], numbers }, '/edit/set-numbers': { question: child } }))
    const onNotice = vi.fn()
    const { editor: e } = make(
      { type: 'doc', content: [questionNode(makeQuestion({ id: 'a', available_ops: ['set-numbers'] }))] },
      vi.fn(),
      onNotice,
    )
    const block = screen.getByTestId('question-block')
    await chooseFromMenu(block, 'Edit numbers…')
    const total = await screen.findByLabelText('Amount shared ($)')
    await fireEvent.input(total, { target: { value: '180' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Apply' }))
    await waitFor(() => expect(texts(e)).toEqual(['a:v2']))
    expect(e.getJSON().content?.[0].attrs?.locked).toBe(true)
    expect(onNotice).toHaveBeenCalledWith(expect.stringContaining('now locked'))
    e.commands.undo()
    expect(texts(e)).toEqual(['a'])
    expect(e.getJSON().content?.[0].attrs?.locked).toBe(false)
  })

  it('opening Edit numbers… closes Edit names…, and the other way round', async () => {
    vi.stubGlobal('fetch', routeFetch({ '/params': { slots: [{ key: 'names', role: 'name', count: 3 }], numbers: [] } }))
    make({ type: 'doc', content: [questionNode(makeQuestion({ id: 'a', available_ops: ['set-numbers'] }))] })
    const block = screen.getByTestId('question-block')
    await chooseFromMenu(block, 'Edit names…')
    expect(await screen.findByRole('form', { name: 'Edit names' })).toBeInTheDocument()
    await chooseFromMenu(block, 'Edit numbers…')
    expect(await screen.findByRole('form', { name: 'Edit numbers' })).toBeInTheDocument()
    expect(screen.queryByRole('form', { name: 'Edit names' })).not.toBeInTheDocument()
    await chooseFromMenu(block, 'Edit names…')
    expect(await screen.findByRole('form', { name: 'Edit names' })).toBeInTheDocument()
    expect(screen.queryByRole('form', { name: 'Edit numbers' })).not.toBeInTheDocument()
  })

  it('shows the API error inside the block and leaves the snapshot alone', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: false, status: 422, text: async () => 'nope' }),
    )
    const { editor: e } = make(two())
    await chooseFromMenu(screen.getAllByTestId('question-block')[0], 'Make harder')
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent("The question wasn't changed. The server couldn't accept this"))
    expect(texts(e)).toEqual(['a', 'b'])
  })

  it('draws a bank question with no on-page tags and no engine-only edits', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(
        routeFetch({
          '/render/question.css': '.q{}',
          '/render/katex.js': '',
          '/render/question': { html: '<div class="frag">bank question html</div>' },
        }),
      ),
    )
    make({ type: 'doc', content: [questionNode(makeBankQuestion())] })
    // Status lives in the inspector, never on the page (EXA-93).
    for (const tag of ['From my bank', 'Unreviewed', 'engine-verified']) {
      expect(screen.queryByText(tag)).not.toBeInTheDocument()
    }
    const labels = await menuLabels(screen.getByTestId('question-block'))
    for (const name of ['Another like this', 'Make harder', 'Edit names…', 'Lock', 'Replace with my own question']) {
      expect(labels).not.toContain(name)
    }
    // …but it still goes in the key or not, adds below, deletes, and can become your own text.
    expect(labels).toEqual(['Leave out of answer key', 'Add question below', 'Edit as my own text…', 'Delete'])
    await waitFor(() =>
      expect(screen.getByTestId('fragment').shadowRoot?.textContent).toContain('bank question html'),
    )
  })

  it('draws a generated multi-part question with the engine renderer and keeps its edits', async () => {
    const bodies: Array<{ question: { id: string } }> = []
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(
        routeFetch({
          '/render/question.css': '.q{}',
          '/render/katex.js': '',
          '/render/question': (init?: RequestInit) => {
            bodies.push(JSON.parse(String(init?.body)))
            return { html: '<div class="frag">(a) distance (b) average speed</div>' }
          },
        }),
      ),
    )
    make({ type: 'doc', content: [questionNode(makeMultipartQuestion())] })
    await waitFor(() =>
      expect(screen.getByTestId('fragment').shadowRoot?.textContent).toContain('(b) average speed'),
    )
    expect(bodies[0].question.id).toBe('speed_structured:1')
    // The engine's whole-question edits stay ("Regenerate" is "Another like this"); nothing else.
    expect(await pillButton(screen.getByTestId('question-block'), 'Another like this')).toBeInTheDocument()
    expect(await menuLabels(screen.getByTestId('question-block'))).not.toContain('Make harder')
    await selectBlock(screen.getByTestId('question-block'))
  })
})
