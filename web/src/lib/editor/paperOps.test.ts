import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/svelte'
import EditorPage from './EditorPage.svelte'
import { cleanNode } from './doc'
import { makeBankQuestion, makeQuestion } from './fixtures'
import { hasGeneratedSlots, regenerateCounts, regenerateNotice, swapNotice } from './paperOps'

const fetchMock = vi.fn()
beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => vi.unstubAllGlobals())

const slot = { marks: 3, kind: 'short' }
const generated = (id: string, text: string, extra: Record<string, unknown> = {}) => ({
  type: 'templatedQuestion',
  attrs: { block_id: id, question: makeQuestion({ id: `ratio_medium:${id}` }, text), slot, ...extra },
})
const placeholder = (id: string) => ({
  type: 'freeformQuestion',
  attrs: { block_id: id, marks: 3, slot: { ...slot, placeholder: true } },
  content: [{ type: 'paragraph' }],
})
const record = (content: unknown[], version = 4) => ({
  id: 'd1',
  title: 'P6 Paper 2',
  total_marks: 6,
  version,
  created_at: '2026-11-15T00:00:00Z',
  updated_at: '2026-11-15T00:00:00Z',
  document: { schema_version: '1.11.0', title: 'P6 Paper 2', content: { type: 'doc', content } },
})
const ok = (body: unknown) => ({ ok: true, status: 200, json: async () => body })

/** GET answers with `initial`; POSTs to /swap or /regenerate answer with `reply`. */
function serve(initial: unknown[], reply: () => unknown) {
  const calls: Array<{ url: string; body: unknown }> = []
  fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
    const u = String(url)
    if (u.endsWith('/swap') || u.endsWith('/regenerate')) {
      calls.push({ url: u, body: JSON.parse(String(init?.body)) })
      return ok(reply())
    }
    if (init?.method === 'PUT') return ok(record(initial, 5))
    return ok(record(initial))
  })
  return calls
}

async function open() {
  render(EditorPage, { props: { id: 'd1' } })
  await waitFor(() => expect(screen.getByLabelText('Paper title')).toHaveValue('P6 Paper 2'))
}

describe('paper ops helpers (P8d)', () => {
  it('knows when a paper has generated positions', () => {
    expect(hasGeneratedSlots({ type: 'doc', content: [generated('gq1', 'x')] })).toBe(true)
    expect(hasGeneratedSlots({ type: 'doc', content: [placeholder('gq2')] })).toBe(true)
    expect(
      hasGeneratedSlots({ type: 'doc', content: [{ type: 'templatedQuestion', attrs: { slot: null } }] }),
    ).toBe(false)
  })

  it('counts what "Regenerate unlocked" would replace and keep', () => {
    const doc = {
      type: 'doc' as const,
      content: [
        generated('gq1', 'x'),
        generated('gq2', 'y', { locked: true }),
        placeholder('gq3'),
        // a placeholder the teacher has written in is theirs now: never refilled, locked or not
        {
          ...placeholder('gq4'),
          content: [{ type: 'paragraph', content: [{ type: 'text', text: 'My own question.' }] }],
        },
        {
          ...placeholder('gq5'),
          attrs: { ...placeholder('gq5').attrs, locked: true },
          content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Also mine.' }] }],
        },
        { type: 'templatedQuestion', attrs: { block_id: 'bank', question: makeBankQuestion() } },
      ],
    }
    expect(regenerateCounts(doc)).toEqual({ unlocked: 2, locked: 1 })
    // only filled placeholders and bank questions: nothing to regenerate
    expect(regenerateCounts({ type: 'doc', content: doc.content.slice(3) })).toEqual({ unlocked: 0, locked: 0 })
  })

  it('says what happened in one line', () => {
    expect(swapNotice({ block_id: 'b', mode: 'topic', marks: 2, placeholder: false, topic: 'Volume' })).toBe(
      'Swapped in a 2-mark Volume question.',
    )
    expect(swapNotice({ block_id: 'b', mode: 'own', marks: 4, placeholder: true })).toMatch(/write your own 4-mark/)
    expect(regenerateNotice({ replaced: 1, kept: 2, placeholders: 3 })).toBe(
      'Regenerated 1 question; kept 2 locked or written by you; 3 left as placeholders.',
    )
  })

  it('stores a lock only when it is on', () => {
    expect(cleanNode(generated('gq1', 'x', { locked: true })).attrs?.locked).toBe(true)
    expect(cleanNode(generated('gq1', 'x', { locked: false })).attrs).not.toHaveProperty('locked')
  })
})

describe('swap and lock in the editor (P8d)', () => {
  it('"Another like this" swaps on the server at the saved version and shows the new question', async () => {
    const calls = serve([generated('gq1', 'Old question.'), generated('gq2', 'Kept question.')], () => ({
      ...record([generated('gq1', 'New question.'), generated('gq2', 'Kept question.')], 5),
      report: { block_id: 'gq1', mode: 'like', marks: 3, placeholder: false, topic: 'Ratio' },
    }))
    await open()
    const block = (await screen.findByText('Old question.')).closest('[data-testid="question-block"]') as HTMLElement
    await fireEvent.click(within(block).getByRole('button', { name: 'Another like this' }))
    expect(await screen.findByText('New question.')).toBeInTheDocument()
    expect(screen.queryByText('Old question.')).not.toBeInTheDocument()
    expect(screen.getByText('Kept question.')).toBeInTheDocument()
    expect(calls).toEqual([{ url: expect.stringMatching(/\/documents\/d1\/swap$/), body: { block_id: 'gq1', mode: 'like', base_version: 4 } }])
    expect(screen.getByText(/Swapped in a 3-mark Ratio question/)).toBeInTheDocument()
    // the server saved it: nothing is pending
    expect(screen.getByRole('status')).toHaveTextContent('Saved')
  })

  it('a locked question cannot be swapped, and the lock is a toggle', async () => {
    serve([generated('gq1', 'Locked one.', { locked: true })], () => ({}))
    await open()
    const block = (await screen.findByText('Locked one.')).closest('[data-testid="question-block"]') as HTMLElement
    const lock = within(block).getByRole('button', { name: 'Locked' })
    expect(lock).toHaveAttribute('aria-pressed', 'true')
    expect(within(block).getByRole('button', { name: 'Another topic' })).toBeDisabled()
    await fireEvent.click(lock)
    await waitFor(() => expect(within(block).getByRole('button', { name: 'Lock' })).toHaveAttribute('aria-pressed', 'false'))
    expect(within(block).getByRole('button', { name: 'Another topic' })).toBeEnabled()
  })

  it('a refusal from the server is shown, and the paper is unchanged', async () => {
    serve([generated('gq1', 'Only one.')], () => undefined)
    fetchMock.mockImplementation(async (url: string) =>
      String(url).endsWith('/swap')
        ? { ok: false, status: 422, json: async () => ({ detail: 'No other 3-mark question from another topic fits this paper.' }) }
        : ok(record([generated('gq1', 'Only one.')])),
    )
    await open()
    const block = (await screen.findByText('Only one.')).closest('[data-testid="question-block"]') as HTMLElement
    await fireEvent.click(within(block).getByRole('button', { name: 'Another topic' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('No other 3-mark question from another topic')
    expect(screen.getByText('Only one.')).toBeInTheDocument()
  })

  it('a placeholder can be filled and locked; a hand-added generated question gets the tools too', async () => {
    const calls = serve([placeholder('gq3'), { type: 'templatedQuestion', attrs: { block_id: 'mine1', question: makeQuestion({}, 'Hand added.') } }], () => ({
      ...record([generated('gq3', 'Filled in.'), { type: 'templatedQuestion', attrs: { block_id: 'mine1', question: makeQuestion({}, 'Hand added.') } }], 5),
      report: { block_id: 'gq3', mode: 'like', marks: 3, placeholder: false, topic: 'Ratio' },
    }))
    await open()
    const hand = (await screen.findByText('Hand added.')).closest('[data-testid="question-block"]') as HTMLElement
    // "Regenerate unlocked" refills it, so it can be locked (and swapped) like a slotted one
    expect(within(hand).getByRole('button', { name: 'Another like this' })).toBeInTheDocument()
    expect(within(hand).getByRole('button', { name: 'Lock' })).toBeInTheDocument()
    const ff = document.querySelector('.ffblock') as HTMLElement
    expect(within(ff).getByRole('button', { name: 'Lock' })).toBeVisible()
    await fireEvent.click(within(ff).getByRole('button', { name: 'Fill with a question' }))
    expect(await screen.findByText('Filled in.')).toBeInTheDocument()
    expect(calls[0].body).toEqual({ block_id: 'gq3', mode: 'like', base_version: 4 })
  })

  it('a placeholder can also be filled from another topic', async () => {
    const calls = serve([placeholder('gq3')], () => ({
      ...record([generated('gq3', 'From elsewhere.')], 5),
      report: { block_id: 'gq3', mode: 'topic', marks: 3, placeholder: false, topic: 'Volume' },
    }))
    await open()
    const ff = await waitFor(() => document.querySelector('.ffblock') as HTMLElement)
    await fireEvent.click(within(ff).getByRole('button', { name: 'Another topic' }))
    expect(await screen.findByText('From elsewhere.')).toBeInTheDocument()
    expect(calls[0].body).toEqual({ block_id: 'gq3', mode: 'topic', base_version: 4 })
  })

  it('"Regenerate unlocked" shows on a generated paper and applies what the server made', async () => {
    const calls = serve([generated('gq1', 'Before.'), generated('gq2', 'Locked.', { locked: true })], () => ({
      ...record([generated('gq1', 'After.'), generated('gq2', 'Locked.', { locked: true })], 5),
      report: { replaced: 1, kept: 1, placeholders: 0 },
    }))
    await open()
    await screen.findByText('Before.')
    const regen = screen.getByRole('button', { name: 'Regenerate 1 unlocked…' })
    regen.focus()
    await fireEvent.click(regen)
    // An in-page confirmation names what happens; nothing is sent until it is accepted.
    const dialog = screen.getByRole('alertdialog', { name: 'Regenerate unlocked questions?' })
    expect(dialog).toHaveTextContent('Replaces 1 unlocked question. 1 locked question stays.')
    expect(calls).toHaveLength(0)
    await fireEvent.click(within(dialog).getByRole('button', { name: 'Regenerate' }))
    expect(await screen.findByText('After.')).toBeInTheDocument()
    expect(screen.getByText('Locked.')).toBeInTheDocument()
    expect(calls[0]).toEqual({ url: expect.stringMatching(/\/regenerate$/), body: { base_version: 4 } })
    expect(screen.getByText(/Regenerated 1 question; kept 1/)).toBeInTheDocument()
    // focus waited out the operation (the button disabled, the page inert) and came back
    await waitFor(() => expect(regen).toHaveFocus())
  })

  it('bank questions get no paper tools, and a paper of only those no "Regenerate unlocked"', async () => {
    serve([{ type: 'templatedQuestion', attrs: { block_id: 'bank1', question: makeBankQuestion() } }], () => ({}))
    await open()
    const block = await waitFor(() => screen.getByTestId('question-block'))
    expect(within(block).queryByRole('button', { name: 'Another like this' })).toBeNull()
    expect(within(block).queryByRole('button', { name: 'Lock' })).toBeNull()
    expect(screen.queryByRole('button', { name: /Regenerate .*unlocked/ })).toBeNull()
  })

  it('an edit made while a swap is out never puts the old question back, and is saved after it', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    try {
      let answer: (v: unknown) => void = () => {}
      const puts: Array<{ base: number; doc: { title: string; content: { content: Array<{ attrs: Record<string, unknown> }> } } }> = []
      const initial = [generated('gq1', 'Old question.'), generated('gq2', 'Other question.')]
      fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
        const u = String(url)
        if (u.endsWith('/swap')) return new Promise((r) => (answer = r))
        if (init?.method === 'PUT') {
          const body = JSON.parse(String(init.body))
          puts.push({ base: body.base_version, doc: body.document })
          return ok(record(body.document.content.content, body.base_version + 1))
        }
        return ok(record(initial))
      })
      await open()
      const old = (await screen.findByText('Old question.')).closest('[data-testid="question-block"]') as HTMLElement
      const other = screen.getByText('Other question.').closest('[data-testid="question-block"]') as HTMLElement
      await fireEvent.click(within(old).getByRole('button', { name: 'Another like this' }))
      // The page is inert, but say a change gets through anyway: a lock on another question.
      await fireEvent.click(within(other).getByRole('button', { name: 'Lock' }))
      await vi.advanceTimersByTimeAsync(3000) // well past the autosave debounce
      expect(puts).toHaveLength(0) // nothing races the swap
      answer(
        ok({
          ...record([generated('gq1', 'New question.'), generated('gq2', 'Other question.')], 5),
          report: { block_id: 'gq1', mode: 'like', marks: 3, placeholder: false, topic: 'Ratio' },
        }),
      )
      expect(await screen.findByText('New question.')).toBeInTheDocument()
      await vi.advanceTimersByTimeAsync(3000)
      // one save, on the server's version, with the new question and the lock kept
      expect(puts).toHaveLength(1)
      expect(puts[0].base).toBe(5)
      const saved = puts[0].doc.content.content
      expect(JSON.stringify(saved)).toContain('New question.')
      expect(JSON.stringify(saved)).not.toContain('Old question.')
      expect(saved.find((n) => n.attrs?.block_id === 'gq2')?.attrs.locked).toBe(true)
      expect(within(other).getByRole('button', { name: 'Locked' })).toBeInTheDocument()
    } finally {
      vi.useRealTimers()
    }
  })

  // jsdom has no `inert` behaviour; Svelte sets it as the property or the attribute.
  const isInert = (sel: string) => {
    const el = document.querySelector(sel) as (HTMLElement & { inert?: boolean }) | null
    return !!el && (el.inert === true || el.hasAttribute('inert'))
  }

  it('cancelling the confirmation regenerates nothing', async () => {
    const calls = serve([generated('gq1', 'Q.')], () => ({}))
    await open()
    await screen.findByText('Q.')
    await fireEvent.click(screen.getByRole('button', { name: 'Regenerate 1 unlocked…' }))
    expect(screen.getByRole('alertdialog')).toHaveTextContent('No questions are locked.')
    await fireEvent.keyDown(screen.getByRole('alertdialog'), { key: 'Escape' })
    expect(screen.queryByRole('alertdialog')).toBeNull()
    expect(calls).toHaveLength(0)
  })

  it('the page is inert while the server works', async () => {
    let answer: (v: unknown) => void = () => {}
    fetchMock.mockImplementation(async (url: string) =>
      String(url).endsWith('/regenerate') ? new Promise((r) => (answer = r)) : ok(record([generated('gq1', 'Q.')])),
    )
    await open()
    await screen.findByText('Q.')
    await fireEvent.click(screen.getByRole('button', { name: 'Regenerate 1 unlocked…' }))
    await fireEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Regenerate' }))
    await waitFor(() => expect(isInert('.desk')).toBe(true))
    expect(isInert('.ehead')).toBe(true)
    answer(ok({ ...record([generated('gq1', 'Q2.')], 5), report: { replaced: 1, kept: 0, placeholders: 0 } }))
    await screen.findByText('Q2.')
    expect(isInert('.desk')).toBe(false)
  })
})
