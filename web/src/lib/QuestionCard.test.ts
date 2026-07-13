import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/svelte'
import QuestionCard from './QuestionCard.svelte'
import type { Question } from './types'

const question: Question = {
  id: 'q1',
  seed: 42,
  blueprint_code: 'ratio_medium',
  validation: { status: 'pass' },
  cognitive: { difficulty: 'medium' },
  question: {
    total_marks: 3,
    parts: [
      {
        text: 'Anna and Ben share $90 in the ratio 2 : 3.',
        marks: 3,
        answer: { type: 'quantity', value: 54, unit: '$' },
        solution_steps: [{ text: 'Total units = 5' }],
        marking_scheme: [{ type: 'M', mark: 1, description: 'Finds 1 unit = $18' }],
        diagram: null,
      },
    ],
  },
}

describe('QuestionCard', () => {
  it('renders the question text, pass badge, and $-formatted answer', () => {
    render(QuestionCard, { props: { q: question } })

    expect(screen.getByText(question.question.parts[0].text)).toBeInTheDocument()
    expect(screen.getByText('pass')).toBeInTheDocument()
    // fmtAnswer renders a "$" quantity as "$54".
    expect(screen.getByText(/\$54/)).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: /Worked solution/i }),
    ).toBeInTheDocument()
  })

  it('reveals the M/A/B marking scheme only after the toggle is clicked', async () => {
    render(QuestionCard, { props: { q: question } })

    // Collapsed by default.
    expect(screen.queryByText('Finds 1 unit = $18')).not.toBeInTheDocument()

    const toggle = screen.getByRole('button', {
      name: /detailed answer key \(M\/A\/B\)/i,
    })
    await fireEvent.click(toggle)

    expect(screen.getByText('Finds 1 unit = $18')).toBeInTheDocument()
    expect(screen.getByText('M')).toBeInTheDocument()
  })
})
