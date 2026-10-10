import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/svelte'
import QuestionCard from './QuestionCard.svelte'
import QuestionBody from './editor/QuestionBody.svelte'
import { fmtAnswer } from './format'
import type { Question } from './types'

const fetchMock = vi.fn()
beforeEach(() => {
  fetchMock.mockReset()
  // The engine draws the server-side figures: echo the view so each option is distinguishable.
  fetchMock.mockImplementation(async (_url: string, init: { body: string }) => {
    const spec = JSON.parse(init.body).diagram
    return { ok: true, json: async () => ({ svg: `<svg data-testid="fig-${spec.view}"></svg>` }) }
  })
  vi.stubGlobal('fetch', fetchMock)
})

const stack = (view: string) => ({
  type: 'cube_stack' as const,
  heights: [
    [2, 1, 0],
    [1, 3, 1],
  ],
  view,
})

const mcq: Question = {
  id: 'sourced:x',
  seed: 0,
  blueprint_code: '',
  validation: { status: 'pass' },
  question: {
    stem: 'The figure shows a stack of cubes.',
    diagram: stack('iso'),
    total_marks: 1,
    parts: [
      {
        text: 'Which picture shows the stack from the front?',
        marks: 1,
        diagram: null,
        answer: {
          type: 'choice',
          correct: 'B',
          options: [
            { label: 'A', diagram: stack('side') },
            { label: 'B', diagram: stack('front') },
            { label: 'C', text: 'None of these' },
          ],
        },
      },
    ],
  },
}

describe('stem figures and multiple-choice options', () => {
  for (const [name, Comp] of [
    ['QuestionCard', QuestionCard],
    ['QuestionBody', QuestionBody],
  ] as const) {
    it(`${name} draws the stem, its figure and every option with its figure`, async () => {
      render(Comp, { props: { q: mcq } })
      expect(screen.getByText('The figure shows a stack of cubes.')).toBeInTheDocument()
      await waitFor(() => expect(screen.getByTestId('fig-iso')).toBeInTheDocument())
      const options = within(screen.getByRole('list', { name: 'options' }))
      await waitFor(() => expect(options.getByTestId('fig-front')).toBeInTheDocument())
      expect(options.getByTestId('fig-side')).toBeInTheDocument()
      expect(options.getByText('None of these')).toBeInTheDocument()
      expect(options.getAllByRole('listitem')).toHaveLength(3)
    })
  }

  it('shows only the correct label as the answer, never a JSON dump', () => {
    render(QuestionCard, { props: { q: mcq } })
    const answer = screen.getByText('Answer').parentElement as HTMLElement
    expect(answer).toHaveTextContent(/^Answer\s*B$/)
    expect(screen.queryByText(/"type"/)).not.toBeInTheDocument()
  })

  it('a card without a stem or options is unchanged', () => {
    const plain: Question = {
      ...mcq,
      question: {
        total_marks: 1,
        parts: [{ text: 'Plain.', marks: 1, answer: { type: 'integer', value: 4 } }],
      },
    }
    render(QuestionBody, { props: { q: plain } })
    expect(screen.queryByRole('list', { name: 'options' })).not.toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })
})

describe('fmtAnswer for choice and expression', () => {
  it('names the correct choice (with its text when it has one)', () => {
    expect(fmtAnswer(mcq.question.parts[0].answer)).toBe('B')
    expect(
      fmtAnswer({ type: 'choice', correct: 'C', options: [{ label: 'C', text: 'None' }] }),
    ).toBe('C. None')
  })
  it('prints expression terms plainly', () => {
    expect(
      fmtAnswer({
        type: 'expression',
        unit: 'm',
        terms: [
          { coefficient: 42, symbol: 'π' },
          { coefficient: 84, symbol: null },
        ],
      }),
    ).toBe('42π + 84 m')
    expect(
      fmtAnswer({
        type: 'expression',
        terms: [
          { coefficient: 1, symbol: 'n', power: 2 },
          { coefficient: -3, symbol: 'n' },
          { coefficient: -5, symbol: null },
        ],
      }),
    ).toBe('n^2 - 3n - 5')
  })
})
