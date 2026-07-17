import { describe, it, expect } from 'vitest'
import {
  renderDiagram,
  type BarModelSpec,
  type BarModelBeforeAfterSpec,
  type ShadedFractionSpec,
  type DiagramSpec,
} from './barModel'

// Layout constants mirrored from barModel.ts so the expected geometry below is
// spelled out explicitly rather than recomputed from the module under test.
const LABEL_W = 96
const UNIT_W = 34
const BAR_H = 30
const ROW_GAP = 12
const PAD = 16

const count = (haystack: string, needle: string): number =>
  haystack.split(needle).length - 1

describe('renderDiagram — dispatch and unknowns', () => {
  it('returns "" for null / undefined', () => {
    expect(renderDiagram(null)).toBe('')
    expect(renderDiagram(undefined)).toBe('')
  })

  it('returns "" for an unrecognised spec type', () => {
    expect(renderDiagram({ type: 'pie_chart' } as unknown as DiagramSpec)).toBe('')
  })
})

describe('bar_model geometry', () => {
  it('sizes the canvas and bars from unit counts', () => {
    const spec: BarModelSpec = {
      type: 'bar_model',
      bars: [
        { label: 'Anna', units: 3 },
        { label: 'Ben', units: 2 },
      ],
    }
    const svg = renderDiagram(spec)

    // width = LABEL_W + maxUnits*UNIT_W + PAD_RIGHT(24); maxUnits = 3.
    // height = PAD + (2*BAR_H + 1*ROW_GAP) + PAD = 16 + 72 + 16.
    const expectedWidth = LABEL_W + 3 * UNIT_W + 24 // 222
    const expectedHeight = PAD + (2 * BAR_H + ROW_GAP) + PAD // 104
    expect(svg).toContain(`viewBox="0 0 ${expectedWidth} ${expectedHeight}"`)
    expect(svg).toContain(`width="${expectedWidth}" height="${expectedHeight}"`)

    // Anna's bar: 3 units wide, top row.
    expect(svg).toContain(`x="${LABEL_W}" y="${PAD}" width="${3 * UNIT_W}" height="${BAR_H}"`)
    // Ben's bar: 2 units wide, second row at y = PAD + BAR_H + ROW_GAP.
    const benY = PAD + BAR_H + ROW_GAP
    expect(svg).toContain(`x="${LABEL_W}" y="${benY}" width="${2 * UNIT_W}" height="${BAR_H}"`)

    // Two bars → two rects; internal division lines = (3-1) + (2-1) = 3.
    expect(count(svg, '<rect')).toBe(2)
    expect(count(svg, '<line')).toBe(3)
    // Labels are rendered as <text> anchored to the bar's left.
    expect(svg).toContain('>Anna</text>')
    expect(svg).toContain('>Ben</text>')
  })

  it('escapes special characters in labels', () => {
    const spec: BarModelSpec = {
      type: 'bar_model',
      bars: [{ label: 'A & <B>', units: 1 }],
    }
    const svg = renderDiagram(spec)
    expect(svg).toContain('A &amp; &lt;B&gt;')
    expect(svg).not.toContain('A & <B>')
  })

  it('draws a total brace with its label when total_bracket is present', () => {
    const spec: BarModelSpec = {
      type: 'bar_model',
      bars: [{ label: 'A', units: 2 }],
      total_bracket: { label: '$90' },
    }
    const svg = renderDiagram(spec)
    expect(count(svg, '<path')).toBe(1)
    expect(svg).toContain('>$90</text>')
  })

  it('adds annotation rows (tick line + two end ticks + label) and grows height', () => {
    const bare: BarModelSpec = { type: 'bar_model', bars: [{ label: 'A', units: 2 }] }
    const annotated: BarModelSpec = {
      ...bare,
      annotations: [{ from_unit: 0, to_unit: 2, label: '?' }],
    }
    const bareSvg = renderDiagram(bare)
    const annSvg = renderDiagram(annotated)

    // Annotation block adds ANN_GAP(14) + ANN_ROW_H(26) to the height.
    const bareH = PAD + BAR_H + PAD // 62
    const annH = PAD + BAR_H + 14 + 26 + PAD // 102
    expect(bareSvg).toContain(`height="${bareH}"`)
    expect(annSvg).toContain(`height="${annH}"`)

    // The bare bar has 1 internal line (2 units); the annotation adds 3 more.
    expect(count(bareSvg, '<line')).toBe(1)
    expect(count(annSvg, '<line')).toBe(4)
    expect(annSvg).toContain('>?</text>')
  })

  it('handles an empty bar list without dividing by anything', () => {
    const svg = renderDiagram({ type: 'bar_model', bars: [] })
    // maxUnits clamps to 1 → width = 96 + 34 + 24 = 154; height = 16 + 0 + 16.
    expect(svg).toContain(`viewBox="0 0 ${LABEL_W + UNIT_W + 24} ${PAD + PAD}"`)
    expect(count(svg, '<rect')).toBe(0)
  })
})

describe('bar_model_before_after geometry', () => {
  const spec: BarModelBeforeAfterSpec = {
    type: 'bar_model_before_after',
    stages: [
      {
        name: 'Before',
        bars: [
          { label: 'A', units: 2 },
          { label: 'B', units: 3 },
        ],
      },
      {
        name: 'After',
        bars: [
          { label: 'A', units: 4 },
          { label: 'B', units: 3 },
        ],
      },
    ],
    total_bracket: { label: '90' },
    annotations: [{ label: 'A gains 2 units' }],
  }

  it('renders both stage headings in bold', () => {
    const svg = renderDiagram(spec)
    expect(svg).toContain('font-weight="bold">Before</text>')
    expect(svg).toContain('font-weight="bold">After</text>')
  })

  it('renders four bars, the invariant brace, and the annotation label', () => {
    const svg = renderDiagram(spec)
    expect(count(svg, '<rect')).toBe(4)
    expect(count(svg, '<path')).toBe(1) // total brace on B's last bar
    expect(svg).toContain('>90</text>')
    expect(svg).toContain('>A gains 2 units</text>')
  })
})

describe('shaded_fraction geometry', () => {
  const SHADE = 'fill="#2f5fe0"'
  const filled = (svg: string): number => count(svg, SHADE)

  const spec = (
    shape: ShadedFractionSpec['shape'],
    total: number,
    shaded: number,
  ): ShadedFractionSpec => ({ type: 'shaded_fraction', shape, total_parts: total, shaded_parts: shaded })

  it('rectangle → one rect per part, first shaded_parts filled', () => {
    const svg = renderDiagram(spec('rectangle', 8, 3))
    expect(svg.startsWith('<svg')).toBe(true)
    expect(count(svg, '<rect')).toBe(8)
    expect(filled(svg)).toBe(3)
  })

  it('bar → one horizontal strip per part', () => {
    const svg = renderDiagram(spec('bar', 4, 1))
    expect(count(svg, '<rect')).toBe(4)
    expect(filled(svg)).toBe(1)
  })

  it('circle → one pie sector per part', () => {
    const svg = renderDiagram(spec('circle', 6, 5))
    expect(count(svg, '<path')).toBe(6)
    expect(filled(svg)).toBe(5)
  })

  it('circle with a single part is a whole circle', () => {
    const svg = renderDiagram(spec('circle', 1, 1))
    expect(count(svg, '<circle')).toBe(1)
    expect(count(svg, '<path')).toBe(0)
    expect(filled(svg)).toBe(1)
  })

  it('none shaded → no filled cells', () => {
    expect(filled(renderDiagram(spec('rectangle', 4, 0)))).toBe(0)
  })

  it('is deterministic', () => {
    expect(renderDiagram(spec('circle', 7, 4))).toBe(renderDiagram(spec('circle', 7, 4)))
  })
})
