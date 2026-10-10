import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/svelte'
import ServerDiagram from './ServerDiagram.svelte'
import QuestionCard from './QuestionCard.svelte'
import { isServerDiagram, renderDiagram, type ServerSpec } from './barModel'
import type { Question } from './types'

const fetchMock = vi.fn()
beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})

const chart: ServerSpec = {
  type: 'chart',
  kind: 'pie',
  sectors: [
    { label: 'A', value: 60 },
    { label: 'B', value: 40 },
  ],
}

describe('server-rendered figures', () => {
  it('identifies the types the web cannot draw itself', () => {
    for (const type of ['chart', 'solid', 'number_line', 'panels', 'cube_stack'] as const) {
      expect(isServerDiagram({ type })).toBe(true)
      expect(renderDiagram({ type })).toBe('') // no TS mirror, by design
    }
    expect(isServerDiagram({ type: 'bar_model', bars: [] } as never)).toBe(false)
    expect(isServerDiagram(null)).toBe(false)
  })

  it('fetches the engine SVG and shows it', async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ svg: '<svg data-testid="fig"><text>Apple</text></svg>' }),
    })
    render(ServerDiagram, { props: { spec: chart } })
    expect(screen.getByText(/Drawing figure/)).toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId('fig')).toBeInTheDocument())
    const [url, init] = fetchMock.mock.calls[0]
    expect(String(url)).toMatch(/\/render\/diagram$/)
    expect(JSON.parse(init.body)).toEqual({ diagram: chart })
  })

  it('says so when the engine rejects the figure', async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 422, text: async () => 'invalid diagram' })
    render(ServerDiagram, { props: { spec: { ...chart, title: 'rejected' } } })
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(/could not be drawn/))
  })

  it('a generated chart question card draws its figure via the engine', async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ svg: '<svg data-testid="card-fig"></svg>' }),
    })
    const q: Question = {
      id: 'statistics_chart_medium:1',
      seed: 1,
      blueprint_code: 'statistics_chart_medium',
      validation: { status: 'pass' },
      cognitive: { difficulty: 'medium' },
      available_ops: [],
      question: {
        total_marks: 2,
        parts: [
          {
            text: 'How many pupils chose A?',
            marks: 2,
            answer: { type: 'integer', value: 12, unit: '' },
            solution_steps: [],
            marking_scheme: [],
            diagram: { ...chart, title: 'on a card' },
          },
        ],
      },
    }
    render(QuestionCard, { props: { q } })
    await waitFor(() => expect(screen.getByTestId('card-fig')).toBeInTheDocument())
  })
})
