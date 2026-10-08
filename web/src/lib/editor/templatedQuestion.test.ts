// The W1c spike, kept as a regression test: a Svelte 5 component lives inside a
// ProseMirror node view, survives node updates, reports edits back into the document,
// and is torn down on delete.
import { describe, it, expect, afterEach, vi } from 'vitest'
import { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { fireEvent, screen, waitFor } from '@testing-library/svelte'
import { TemplatedQuestion, questionNode } from './templatedQuestion'
import { makeQuestion } from './fixtures'
import type { DocJSON } from './doc'

let editor: Editor | null = null
afterEach(() => {
  editor?.destroy()
  editor = null
  vi.unstubAllGlobals()
})

function make(content: DocJSON, onAddBelow = vi.fn()) {
  const el = document.createElement('div')
  document.body.appendChild(el)
  editor = new Editor({
    element: el,
    extensions: [StarterKit, TemplatedQuestion.configure({ onAddBelow })],
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

  it('round-trips block_id and the frozen snapshot through getJSON', () => {
    const doc = two()
    const { editor: e } = make(doc)
    const out = e.getJSON().content ?? []
    expect(out[0].attrs?.block_id).toBe(doc.content[0].attrs?.block_id)
    expect((out[1].attrs?.question as { id: string }).id).toBe('b')
  })

  it('removes the block (and unmounts its component) on Delete', async () => {
    const { editor: e } = make(two())
    const del = screen.getAllByRole('button', { name: 'Delete' })[0]
    await fireEvent.click(del)
    await waitFor(() => expect(screen.queryByText('First question text.')).not.toBeInTheDocument())
    expect(texts(e)).toEqual(['b'])
  })

  it('moves a block down and up', async () => {
    const { editor: e } = make(two())
    await fireEvent.click(screen.getAllByRole('button', { name: 'Move down' })[0])
    await waitFor(() => expect(texts(e)).toEqual(['b', 'a']))
    await fireEvent.click(screen.getAllByRole('button', { name: 'Move up' })[1])
    await waitFor(() => expect(texts(e)).toEqual(['a', 'b']))
  })

  it('asks the page to open the picker after the block', async () => {
    const { onAddBelow } = make(two())
    await fireEvent.click(screen.getAllByRole('button', { name: '+ Add below' })[0])
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
    await fireEvent.click(screen.getAllByRole('button', { name: 'Regenerate' })[0])
    await waitFor(() => expect(screen.getByText('Regenerated question text.')).toBeInTheDocument())
    expect(texts(e)).toEqual(['a:v2', 'b'])
    expect(screen.queryByText('First question text.')).not.toBeInTheDocument()
  })

  it('shows the API error inside the block and leaves the snapshot alone', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: false, status: 422, text: async () => 'nope' }),
    )
    const { editor: e } = make(two())
    await fireEvent.click(screen.getAllByRole('button', { name: 'Make harder' })[0])
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('API 422: nope'))
    expect(texts(e)).toEqual(['a', 'b'])
  })
})
