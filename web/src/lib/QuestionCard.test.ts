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

  it('dispatches an approve event carrying the question', async () => {
    let payload: { q: Question } | undefined
    render(QuestionCard, {
      props: { q: question },
      events: { approve: (e: CustomEvent<{ q: Question }>) => (payload = e.detail) },
    })

    await fireEvent.click(screen.getByRole('button', { name: 'Approve' }))

    expect(payload?.q.id).toBe('q1')
  })

  it('dispatches a discard event carrying the question id', async () => {
    let payload: { id: string } | undefined
    render(QuestionCard, {
      props: { q: question },
      events: { discard: (e: CustomEvent<{ id: string }>) => (payload = e.detail) },
    })

    await fireEvent.click(screen.getByRole('button', { name: 'Discard' }))

    expect(payload?.id).toBe('q1')
  })

  it('shows the Added state and disables Approve + edit buttons when added', () => {
    render(QuestionCard, { props: { q: question, added: true } })

    expect(screen.getByText('✓ Added to worksheet')).toBeInTheDocument()
    // Approve is replaced by the Added state, so it is gone entirely.
    expect(screen.queryByRole('button', { name: 'Approve' })).not.toBeInTheDocument()

    // All edit buttons are disabled.
    for (const name of [
      'Regenerate',
      'Make easier',
      'Make harder',
      'Change to decimals',
      'Show diagram',
    ]) {
      expect(screen.getByRole('button', { name })).toBeDisabled()
    }

    // Discard stays available (client-only remove from the review list).
    expect(screen.getByRole('button', { name: 'Discard' })).not.toBeDisabled()
  })

  // A geometry card carries a mandatory figure: the API's available_ops omits
  // toggle-diagram, and the card correspondingly renders no Show/Hide button.
  const geometryQuestion: Question = {
    id: 'g1',
    seed: 7,
    blueprint_code: 'geometry_area_hard',
    validation: { status: 'pass' },
    cognitive: { difficulty: 'hard' },
    question: {
      total_marks: 3,
      parts: [
        {
          text: 'Find the area of the shaded region.',
          marks: 3,
          answer: { type: 'quantity', value: 24, unit: 'cm²' },
          diagram: {
            type: 'geometry_figure',
            points: [
              { id: 'A', x: 0, y: 0 },
              { id: 'B', x: 6, y: 0 },
              { id: 'C', x: 6, y: 4 },
              { id: 'D', x: 0, y: 4 },
            ],
            segments: [
              { from: 'A', to: 'B', label: '6 cm' },
              { from: 'B', to: 'C' },
              { from: 'C', to: 'D' },
              { from: 'D', to: 'A', label: '4 cm' },
            ],
            shaded: [{ boundary: ['A', 'B', 'C', 'D'] }],
          },
        },
      ],
    },
  }

  it('renders a geometry_figure SVG and shows no toggle-diagram button', () => {
    render(QuestionCard, { props: { q: geometryQuestion } })

    // The figure renders as an inline SVG, labelled as a geometry figure.
    const fig = screen.getByLabelText('geometry figure')
    expect(fig.querySelector('svg')).not.toBeNull()

    // Mandatory figure → no Show/Hide diagram control at all.
    expect(screen.queryByRole('button', { name: /diagram/i })).not.toBeInTheDocument()
  })

  it('renders a shaded_fraction SVG and shows no toggle-diagram button', () => {
    const shadedQuestion: Question = {
      id: 'f1',
      seed: 3,
      blueprint_code: 'fractions_easy',
      validation: { status: 'pass' },
      cognitive: { difficulty: 'easy' },
      question: {
        total_marks: 1,
        parts: [
          {
            text: 'What fraction of the shape is shaded?',
            marks: 1,
            answer: { type: 'fraction', numerator: 1, denominator: 4 },
            diagram: { type: 'shaded_fraction', shape: 'rectangle', total_parts: 4, shaded_parts: 1 },
          },
        ],
      },
    }
    render(QuestionCard, { props: { q: shadedQuestion } })

    const fig = screen.getByLabelText('fraction diagram')
    expect(fig.querySelector('svg')).not.toBeNull()

    expect(screen.queryByRole('button', { name: /diagram/i })).not.toBeInTheDocument()
  })
})
