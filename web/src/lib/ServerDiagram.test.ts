import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/svelte'
import ServerDiagram from './ServerDiagram.svelte'
import DiagramView from './DiagramView.svelte'
import QuestionCard from './QuestionCard.svelte'
import * as diagramModule from './diagram'
import type { DiagramSpec, ServerSpec } from './diagram'
import type { Question } from './types'

const fetchMock = vi.fn()
beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})

const svgReply = (testid: string) => ({
  ok: true,
  json: async () => ({ svg: `<svg data-testid="${testid}"><text>engine</text></svg>` }),
})

const chart: ServerSpec = {
  type: 'chart',
  kind: 'pie',
  sectors: [
    { label: 'A', value: 60 },
    { label: 'B', value: 40 },
  ],
}

// The types the web used to draw with its own TypeScript renderer (EXA-151).
const formerlyClientDrawn: Array<[string, DiagramSpec]> = [
  ['bar model', { type: 'bar_model', bars: [{ label: 'Ali', units: 2 }] }],
  [
    'bar model',
    {
      type: 'bar_model_before_after',
      view_mode: 'sliced',
      stages: [{ name: 'Before', bars: [{ label: 'Ali', units: 2 }] }],
    },
  ],
  ['fraction diagram', { type: 'shaded_fraction', shape: 'circle', total_parts: 6, shaded_parts: 5 }],
  [
    'geometry figure',
    {
      type: 'geometry_figure',
      points: [
        { id: 'A', x: 0, y: 0 },
        { id: 'B', x: 4, y: 0 },
      ],
      segments: [{ from: 'A', to: 'B', label: '4 cm' }],
    },
  ],
]

describe('server-rendered figures', () => {
  it('the TypeScript renderers are gone: the diagram module draws nothing itself', () => {
    const exported = Object.keys(diagramModule)
    for (const name of ['renderDiagram', 'renderGeometryFigure', 'renderBarModel', 'isServerDiagram']) {
      expect(exported).not.toContain(name)
    }
    const modules = import.meta.glob('./barModel.ts')
    expect(Object.keys(modules)).toHaveLength(0)
  })

  it('fetches the engine SVG and shows it', async () => {
    fetchMock.mockResolvedValue(svgReply('fig'))
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

  it.each(formerlyClientDrawn)('a %s is drawn by the engine, not the browser', async (aria, spec) => {
    fetchMock.mockResolvedValue(svgReply(`server-${spec.type}`))
    const { container } = render(DiagramView, { props: { spec } })
    expect(container.querySelector('svg')).toBeNull() // nothing drawn locally while it loads
    expect(screen.getByText(/Drawing figure/)).toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId(`server-${spec.type}`)).toBeInTheDocument())
    expect(screen.getByLabelText(aria)).toContainElement(screen.getByTestId(`server-${spec.type}`))
    const [url, init] = fetchMock.mock.calls[0]
    expect(String(url)).toMatch(/\/render\/diagram$/)
    expect(JSON.parse(init.body)).toEqual({ diagram: spec })
  })

  it('a raster stays a plain image and needs no engine round trip', () => {
    render(DiagramView, {
      props: { spec: { type: 'raster', asset_ref: 'data:image/png;base64,iVBORw0KGgo=', alt_text: 'A & <B>' } },
    })
    const img = screen.getByAltText('A & <B>')
    expect(img).toHaveAttribute('src', 'data:image/png;base64,iVBORw0KGgo=')
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('a generated chart question card draws its figure via the engine', async () => {
    fetchMock.mockResolvedValue(svgReply('card-fig'))
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
