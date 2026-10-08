import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/svelte'
import AnswerKey from './AnswerKey.svelte'
import { makeQuestion } from './fixtures'

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
})
