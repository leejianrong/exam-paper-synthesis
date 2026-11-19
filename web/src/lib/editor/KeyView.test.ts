import { describe, it, expect, vi, afterEach } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/svelte'
import KeyView, { KEY_REFRESH_MS } from './KeyView.svelte'
import { answerWritten, findKeyRow, keyNumbers, keyRowNumber } from './keyRows'
import { keyOptionsOf } from './layout'
import { freeformDocNode, makeQuestion, templatedNodes } from './fixtures'

const SCHOOL = keyOptionsOf({ key_options: { layout: 'compact', show_scheme: false, show_marks: false, one_mark_working: false } })

function setup(props: Record<string, unknown> = {}) {
  const calls = { style: vi.fn(), option: vi.fn(), include: vi.fn(), answer: vi.fn() }
  let n = 0
  const load = vi.fn(async () => `<p>KEY ${++n}</p>`)
  const view = render(KeyView, {
    props: {
      active: true,
      revision: 1,
      load,
      empty: false,
      options: SCHOOL,
      numbers: [1, 2],
      onStyle: calls.style,
      onOption: calls.option,
      onInclude: calls.include,
      onEditAnswer: calls.answer,
      ...props,
    },
  })
  return { ...calls, load, view }
}

const frames = () => Array.from(document.querySelectorAll('iframe'))

afterEach(() => vi.useRealTimers())

describe('the answer key view (EXA-162)', () => {
  it('shows the printed key from the server, and nothing is fetched while it is hidden', async () => {
    let release = () => {}
    const load = vi.fn(() => new Promise<string>((done) => (release = () => done('<p>KEY</p>'))))
    const hidden = setup({ active: false, load })
    expect(load).not.toHaveBeenCalled()
    await hidden.view.rerender({ active: true })
    // until the key has come and drawn, the view says it is loading
    await waitFor(() => expect(load).toHaveBeenCalledTimes(1))
    expect(screen.getByText('Loading the answer key…')).toBeInTheDocument()
    release()
    await waitFor(() => expect(frames()).toHaveLength(1))
    expect(frames()[0].getAttribute('srcdoc')).toBe('<p>KEY</p>')
    expect(frames()[0]).toHaveAttribute('title', 'Answer key, as it will print')
    await waitFor(() => expect(screen.queryByText('Loading the answer key…')).toBeNull())
  })

  it('refreshes a moment after the last edit, once the edits stop', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const { load, view } = setup()
    await waitFor(() => expect(frames()).toHaveLength(1))
    // three quick edits: one request, once they stop
    await view.rerender({ revision: 2 })
    await view.rerender({ revision: 3 })
    await view.rerender({ revision: 4 })
    await vi.advanceTimersByTimeAsync(KEY_REFRESH_MS - 100)
    expect(load).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(200)
    expect(load).toHaveBeenCalledTimes(2)
    // the new key replaces the old once it has drawn (jsdom draws at once)
    await waitFor(() => expect(frames().map((f) => f.getAttribute('srcdoc'))).toEqual(['<p>KEY 2</p>']))
    expect(frames()[0]).toHaveClass('ready')
  })

  it('says when the key did not load and tries again on request', async () => {
    const { load } = setup()
    load.mockRejectedValueOnce(new Error('API 500: boom'))
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent("The answer key didn't load")
    expect(load).toHaveBeenCalledTimes(1) // no retry loop on its own
    await fireEvent.click(within(alert).getByRole('button', { name: 'Try again' }))
    await waitFor(() => expect(frames()).toHaveLength(1))
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('an empty paper asks for a question instead of loading', () => {
    const { load } = setup({ empty: true })
    expect(load).not.toHaveBeenCalled()
    expect(screen.getByText(/The paper has no questions yet/)).toBeInTheDocument()
  })

  it('the options strip: the school key offers marks and 1-mark working, not the question', async () => {
    const { style, option } = setup()
    const strip = screen.getByRole('group', { name: 'Answer key options' })
    expect(within(strip).getByRole('radio', { name: 'School key' })).toBeChecked()
    expect(within(strip).queryByRole('checkbox', { name: 'The question' })).toBeNull()
    await fireEvent.click(within(strip).getByRole('checkbox', { name: 'Marks' }))
    expect(option).toHaveBeenCalledWith('show_marks', true)
    await fireEvent.click(within(strip).getByRole('checkbox', { name: 'Working for 1-mark questions' }))
    expect(option).toHaveBeenCalledWith('one_mark_working', true)
    await fireEvent.click(within(strip).getByRole('radio', { name: 'Worked solutions' }))
    expect(style).toHaveBeenCalledWith('full')
  })

  it('worked solutions offer the question and the marking scheme', async () => {
    const { option } = setup({ options: keyOptionsOf(undefined) })
    const strip = screen.getByRole('group', { name: 'Answer key options' })
    expect(within(strip).getByRole('radio', { name: 'Worked solutions' })).toBeChecked()
    expect(within(strip).queryByRole('checkbox', { name: 'Marks' })).toBeNull()
    await fireEvent.click(within(strip).getByRole('checkbox', { name: 'The question' }))
    expect(option).toHaveBeenCalledWith('show_question', false)
    await fireEvent.click(within(strip).getByRole('checkbox', { name: 'Marking scheme (M1, A1)' }))
    expect(option).toHaveBeenCalledWith('show_scheme', false)
  })

  it('names the questions left out, with Include, and the answers the teacher writes', async () => {
    const { include, answer } = setup({
      leftOut: [{ n: 3, blockId: 'b3' }],
      own: [
        { n: 1, blockId: 'b1', written: true },
        { n: 2, blockId: 'b2', written: false },
      ],
    })
    await fireEvent.click(screen.getByRole('button', { name: 'Include question 3 in the answer key' }))
    expect(include).toHaveBeenCalledWith('b3')
    const todo = screen.getByRole('button', { name: 'Edit the answer to question 2 (not written yet)' })
    expect(todo).toHaveTextContent('to write')
    await fireEvent.click(screen.getByRole('button', { name: 'Edit the answer to question 1' }))
    expect(answer).toHaveBeenCalledWith('b1')
  })
})

/** A deferred load(): each call waits until the test settles it. */
function deferredLoads() {
  const pending: Array<{ resolve: (html: string) => void; reject: (e: Error) => void }> = []
  const load = vi.fn(() => new Promise<string>((resolve, reject) => pending.push({ resolve, reject })))
  return { load, pending }
}

/** jsdom draws no srcdoc: put the printed key's markup into the frame on screen by hand. */
function draw(html: string) {
  const frame = document.querySelector<HTMLIFrameElement>('iframe.ready')!
  frame.contentDocument!.body.innerHTML = html
  return frame.contentDocument!
}
const WORKED_KEY = '<ol class="questions"><li class="question">first</li><li class="question">second</li></ol>'

describe('the answer key view keeps up with the paper (review of #242)', () => {
  it('a slower, older response that lands after a newer one never replaces it', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const { load, pending } = deferredLoads()
    const { view } = setup({ load })
    await waitFor(() => expect(load).toHaveBeenCalledTimes(1))
    pending[0].resolve('<p>KEY 1</p>')
    await waitFor(() => expect(frames()).toHaveLength(1))
    await view.rerender({ revision: 2 })
    await vi.advanceTimersByTimeAsync(KEY_REFRESH_MS + 10)
    await view.rerender({ revision: 3 })
    await vi.advanceTimersByTimeAsync(KEY_REFRESH_MS + 10)
    expect(load).toHaveBeenCalledTimes(3)
    pending[2].resolve('<p>KEY 3</p>')
    await waitFor(() => expect(frames().map((f) => f.getAttribute('srcdoc'))).toEqual(['<p>KEY 3</p>']))
    pending[1].resolve('<p>KEY 2</p>')
    await vi.advanceTimersByTimeAsync(50)
    expect(frames().map((f) => f.getAttribute('srcdoc'))).toEqual(['<p>KEY 3</p>'])
  })

  it('a failed update keeps the old key on screen and says it did not update', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const { load, pending } = deferredLoads()
    const { view } = setup({ load })
    await waitFor(() => expect(load).toHaveBeenCalledTimes(1))
    pending[0].resolve('<p>KEY 1</p>')
    await waitFor(() => expect(document.querySelector('iframe.ready')).not.toBeNull())
    await view.rerender({ revision: 2 })
    await vi.advanceTimersByTimeAsync(KEY_REFRESH_MS + 10)
    // the old key stays while the new one is asked for
    expect(screen.getByText('Updating…')).toBeInTheDocument()
    pending[1].reject(new Error('API 500: boom'))
    expect(await screen.findByRole('alert')).toHaveTextContent("The answer key didn't update")
    expect(frames().map((f) => f.getAttribute('srcdoc'))).toEqual(['<p>KEY 1</p>'])
    expect(screen.queryByText('Updating…')).toBeNull()
  })

  it('after a failed first load, edits wait for the pause instead of asking on every keystroke', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const { load, pending } = deferredLoads()
    const { view } = setup({ load })
    await waitFor(() => expect(load).toHaveBeenCalledTimes(1))
    pending[0].reject(new Error('offline'))
    await screen.findByRole('alert')
    await view.rerender({ revision: 2 })
    await view.rerender({ revision: 3 })
    await vi.advanceTimersByTimeAsync(KEY_REFRESH_MS - 100)
    expect(load).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(200)
    expect(load).toHaveBeenCalledTimes(2)
  })

  it('waits while the paper is being rewritten (paused), then loads', async () => {
    const { load, view } = setup({ paused: true })
    await new Promise((r) => setTimeout(r, 50))
    expect(load).not.toHaveBeenCalled()
    await view.rerender({ paused: false })
    await waitFor(() => expect(load).toHaveBeenCalledTimes(1))
  })

  it('a click reads the numbers the key on screen was made with, not the paper as it is now', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    // worked solutions for questions 1 and 3 (2 was left out); 3 is the teacher's own
    const { view, answer } = setup({
      options: keyOptionsOf(undefined),
      numbers: [1, 3],
      own: [{ n: 3, blockId: 'b3', written: true }],
    })
    await waitFor(() => expect(document.querySelector('iframe.ready')).not.toBeNull())
    const d = draw(WORKED_KEY)
    // question 2 is included again: until the new key is in, the second solution is still 3's
    await view.rerender({
      revision: 2,
      numbers: [1, 2, 3],
      own: [
        { n: 2, blockId: 'b2', written: true },
        { n: 3, blockId: 'b3', written: true },
      ],
    })
    await fireEvent.click(d.querySelectorAll('li')[1])
    expect(answer).toHaveBeenCalledWith('b3')
    expect(answer).not.toHaveBeenCalledWith('b2')
  })

  it('a scroll waits for the new key while one is due, and goes straight to the row when the key is current', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const scrollTo = vi.fn()
    vi.stubGlobal('scrollTo', scrollTo)
    try {
      const { view } = setup({ options: keyOptionsOf(undefined), numbers: [1, 3] })
      await waitFor(() => expect(document.querySelector('iframe.ready')).not.toBeNull())
      await waitFor(() => expect(screen.queryByText('Updating…')).toBeNull())
      draw(WORKED_KEY)
      const kv = view.component as unknown as { scrollToQuestion: (n: number, m?: number) => boolean }
      expect(kv.scrollToQuestion(3)).toBe(true)
      expect(scrollTo).toHaveBeenCalledTimes(1)
      // an edit is waiting to be drawn: the key on screen may number things differently
      await view.rerender({ revision: 2, numbers: [1, 2, 3] })
      // (on the old key, the second solution would be taken for question 2)
      expect(kv.scrollToQuestion(2)).toBe(false)
      expect(scrollTo).toHaveBeenCalledTimes(1)
    } finally {
      vi.unstubAllGlobals()
    }
  })
})

describe('a scroll that waits for the next key (re-review of #242)', () => {
  /** jsdom draws no srcdoc: give every new frame question 3's row before its load fires. */
  function drawNewFrames() {
    const mo = new MutationObserver(() => {
      for (const f of document.querySelectorAll<HTMLIFrameElement>('iframe:not([data-drawn])')) {
        f.dataset.drawn = ''
        if (f.contentDocument) f.contentDocument.body.innerHTML = '<table class="key-table"><tr><th scope="row">Q3</th><td>w</td></tr></table>'
      }
    })
    mo.observe(document.body, { childList: true, subtree: true })
    return mo
  }

  async function waitingScroll(failFirst: boolean) {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const scrollTo = vi.fn()
    vi.stubGlobal('scrollTo', scrollTo)
    const mo = drawNewFrames()
    try {
      const { load, pending } = deferredLoads()
      const { view } = setup({ load, numbers: [3] })
      await waitFor(() => expect(load).toHaveBeenCalledTimes(1))
      pending[0].resolve('<p>KEY 1</p>')
      await waitFor(() => expect(document.querySelector('iframe.ready')).not.toBeNull())
      // a refresh is due: the scroll waits for the next key
      await view.rerender({ revision: 2 })
      const kv = view.component as unknown as { scrollToQuestion: (n: number, m?: number) => boolean }
      expect(kv.scrollToQuestion(3)).toBe(false)
      await vi.advanceTimersByTimeAsync(KEY_REFRESH_MS + 10)
      expect(load).toHaveBeenCalledTimes(2)
      if (failFirst) {
        pending[1].reject(new Error('offline'))
        await screen.findByRole('alert')
        // a later key loads fine
        await view.rerender({ revision: 3 })
        await vi.advanceTimersByTimeAsync(KEY_REFRESH_MS + 10)
        pending[2].resolve('<p>KEY 3</p>')
      } else {
        pending[1].resolve('<p>KEY 2</p>')
      }
      await waitFor(() => expect(frames().map((f) => f.getAttribute('srcdoc'))).toEqual([failFirst ? '<p>KEY 3</p>' : '<p>KEY 2</p>']))
      await vi.advanceTimersByTimeAsync(50)
      return scrollTo
    } finally {
      mo.disconnect()
      vi.unstubAllGlobals()
    }
  }

  it('lands on the row once the next key has loaded', async () => {
    expect(await waitingScroll(false)).toHaveBeenCalledTimes(1)
  })

  it('is dropped when that load fails: a later key never jumps the page', async () => {
    expect(await waitingScroll(true)).not.toHaveBeenCalled()
  })
})

describe('reading the printed key (keyRows)', () => {
  const doc = (html: string) => new DOMParser().parseFromString(html, 'text/html')
  const SCHOOL_KEY = doc(
    '<table class="key-grid"><tr><th scope="col">Q1</th><th scope="col">Q2</th><th></th></tr>' +
      '<tr><td>3</td><td>1</td><td></td></tr></table>' +
      '<table class="key-table key-pairs"><tbody><tr><th scope="row">Q4</th><td class="key-short">62</td>' +
      '<th scope="row">Q5</th><td class="key-short">7</td></tr></tbody></table>' +
      '<table class="key-table"><tbody><tr><th scope="row">Q6</th><td class="key-work"><p>work</p></td></tr></tbody></table>',
  )
  const WORKED = doc('<ol class="questions"><li class="question">a</li><li class="question">b</li></ol>')

  it('finds a question by its printed label, or by its place among the worked solutions', () => {
    expect(findKeyRow(SCHOOL_KEY, 2, [])?.textContent).toBe('Q2')
    expect(findKeyRow(SCHOOL_KEY, 5, [])?.textContent).toBe('Q5')
    expect(findKeyRow(SCHOOL_KEY, 6, [])?.textContent).toBe('Q6')
    expect(findKeyRow(SCHOOL_KEY, 3, [])).toBeNull()
    // question 2 was left out: the worked solutions are 1 and 3
    expect(findKeyRow(WORKED, 3, [1, 3])?.textContent).toBe('b')
    expect(findKeyRow(WORKED, 2, [1, 3])).toBeNull()
  })

  it('maps a click back to its question', () => {
    const cells = SCHOOL_KEY.querySelectorAll('td')
    expect(keyRowNumber(cells[1], [])).toBe(2) // the grid's second column
    expect(keyRowNumber(SCHOOL_KEY.querySelector('.key-pairs td:last-child')!, [])).toBe(5)
    expect(keyRowNumber(SCHOOL_KEY.querySelector('.key-work p')!, [])).toBe(6)
    expect(keyRowNumber(cells[2], [])).toBeNull() // a padding cell
    expect(keyRowNumber(WORKED.querySelectorAll('li')[1], [1, 3])).toBe(3)
  })

  it('the numbers in the key skip a left-out question; an own answer is written when every part has one', () => {
    const [a, b] = templatedNodes([makeQuestion({ id: 'a' }), makeQuestion({ id: 'b' })])
    const out = { ...b, attrs: { ...b.attrs, in_key: false } }
    expect(keyNumbers([a, out, a], 16)).toEqual([16, 18])
    expect(answerWritten(freeformDocNode({ answer: 'ANS' }))).toBe(true)
    expect(answerWritten(freeformDocNode({ answer: '' }))).toBe(false)
    const parts = freeformDocNode({ answer: 'ANS' })
    parts.content.push({ type: 'freeformPart', attrs: { answer: { type: 'doc', content: [] } }, content: [] } as never)
    expect(answerWritten(parts)).toBe(false)
  })
})
