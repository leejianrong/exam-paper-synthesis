import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/svelte'
import { vi } from 'vitest'
import AnswerKey from './AnswerKey.svelte'
import { makeBankQuestion, makeQuestion, routeFetch } from './fixtures'

describe('AnswerKey', () => {
  it('lists answers, steps and marking in document order with matching numbers', () => {
    const qs = [
      makeQuestion({ id: 'a' }, 'First.'),
      makeQuestion(
        { id: 'b', question: { total_marks: 2, parts: [{ text: 'Second.', marks: 2, answer: { type: 'integer', value: 7, unit: 'cm' } }] } },
        'Second.',
      ),
    ]
    render(AnswerKey, { props: { questions: qs } })
    const entries = document.querySelectorAll('.entry')
    expect(entries).toHaveLength(2)
    expect(entries[0]).toHaveTextContent('1.')
    expect(entries[0]).toHaveTextContent('$40')
    expect(entries[0]).toHaveTextContent('Total units = 2 + 3 + 4 = 9.')
    expect(entries[0]).toHaveTextContent('M1')
    expect(entries[1]).toHaveTextContent('2.')
    expect(entries[1]).toHaveTextContent('7 cm')
  })

  it('shows a placeholder when there are no questions', () => {
    render(AnswerKey, { props: { questions: [] } })
    expect(screen.getByText('Answers appear here as you add questions.')).toBeInTheDocument()
  })

  it('draws a bank question\'s entry with the engine key markup and its own number', async () => {
    const seen: Array<{ mode: string; number: number }> = []
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(
        routeFetch({
          '/render/question.css': '.q{}',
          '/render/katex.js': '',
          '/render/question': (init?: RequestInit) => {
            const b = JSON.parse(String(init?.body))
            seen.push({ mode: b.mode, number: b.number })
            return { html: '<div class="frag">key for bank</div>' }
          },
        }),
      ),
    )
    render(AnswerKey, { props: { questions: [makeQuestion({ id: 'a' }), makeBankQuestion()] } })
    // The generated entry stays hand-built; the bank one is the engine fragment, numbered 2.
    expect(document.querySelectorAll('.entry')).toHaveLength(2)
    await waitFor(() =>
      expect(screen.getByTestId('fragment').shadowRoot?.textContent).toContain('key for bank'),
    )
    expect(seen).toEqual([{ mode: 'key', number: 2 }])
    vi.unstubAllGlobals()
  })
})
