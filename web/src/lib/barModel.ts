// Spec -> inline SVG for the bar-model aid (A5). Mirrors the engine renderer in
// engine/exam_engine/diagram.py: the closed canonical schema stores the *spec*
// (not the SVG), so the live card renders client-side from the same spec while
// the engine renderer serves the eventual PDF path (A7/V5). Deterministic.

const LABEL_W = 96
const UNIT_W = 34
const BAR_H = 30
const ROW_GAP = 12
const PAD_TOP = 16
const PAD_RIGHT = 24
const ANN_ROW_H = 26
const ANN_GAP = 14
const BRACE_GAP = 12
const BRACE_W = 9
const BRACE_LABEL_GAP = 8
const CHAR_W = 7
const STAGE_HEAD_H = 22
const STAGE_GAP = 18

// shaded_fraction layout (mirrors engine/exam_engine/diagram.py).
const SF_CELL = 40
const SF_RECT_H = 80
const SF_BAR_W = 72
const SF_CIRCLE_R = 60
const SF_PAD = 8
const SF_SHADE = '#2f5fe0'
const SF_EMPTY = '#eef2fb'
const SF_STROKE = '#2f5fe0'

export interface BarSpec {
  label: string
  units: number
}

export interface AnnotationSpec {
  label: string
  from_unit?: number
  to_unit?: number
}

export interface TotalBracket {
  label: string
}

export interface StageSpec {
  name: string
  bars?: BarSpec[]
}

export interface BarModelSpec {
  type: 'bar_model'
  bars?: BarSpec[]
  annotations?: AnnotationSpec[]
  total_bracket?: TotalBracket | null
}

export interface BarModelBeforeAfterSpec {
  type: 'bar_model_before_after'
  stages?: StageSpec[]
  annotations?: AnnotationSpec[]
  total_bracket?: TotalBracket | null
}

export interface ShadedFractionSpec {
  type: 'shaded_fraction'
  shape: 'rectangle' | 'circle' | 'bar'
  total_parts: number
  shaded_parts: number
}

export interface GeometryPoint {
  id: string
  x: number
  y: number
}

export interface GeometrySegment {
  from: string
  to: string
  label?: string | null
  ticks?: number
}

export interface GeometryArc {
  center: string
  radius: number
  start_deg: number
  end_deg: number
  label?: string | null
}

export interface GeometryAngle {
  at: string
  from: string
  to: string
  value_deg?: number | null
  unknown?: boolean
  right?: boolean
}

// One boundary edge of a shaded region that is a circular arc rather than a
// straight segment, keyed by its from→to endpoints (mirrors _gf_shaded_edge in
// engine/exam_engine/diagram.py).
export interface GeometryShadedArc {
  from: string
  to: string
  center?: string
  radius: number
  large?: number
  sweep?: number
}

export interface GeometryShaded {
  boundary: string[]
  arcs?: GeometryShadedArc[]
}

export interface GeometryLabel {
  at: string
  text: string
}

export interface GeometryFigureSpec {
  type: 'geometry_figure'
  unit?: string
  points: GeometryPoint[]
  segments?: GeometrySegment[]
  arcs?: GeometryArc[]
  angles?: GeometryAngle[]
  shaded?: GeometryShaded[] | null
  labels?: GeometryLabel[]
}

export interface RasterSpec {
  type: 'raster'
  asset_ref: string
  alt_text: string
}

export type DiagramSpec =
  | BarModelSpec
  | BarModelBeforeAfterSpec
  | ShadedFractionSpec
  | GeometryFigureSpec
  | RasterSpec

function esc(text: string): string {
  return String(text)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
}

/** Render a diagram spec to an inline <svg> string. Returns '' for unknowns. */
export function renderDiagram(spec: DiagramSpec | null | undefined): string {
  if (!spec) return ''
  if (spec.type === 'bar_model') return renderBarModel(spec)
  if (spec.type === 'bar_model_before_after') return renderBarModelBeforeAfter(spec)
  if (spec.type === 'shaded_fraction') return renderShadedFraction(spec)
  if (spec.type === 'geometry_figure') return renderGeometryFigure(spec)
  if (spec.type === 'raster') return renderRaster(spec)
  return ''
}

// raster: a sourced/ingested figure carried verbatim as an image (asset_ref,
// typically a self-contained data: URI). Not an <svg>; mirrors _render_raster in
// engine/exam_engine/diagram.py — the caller wraps it in <figure class="diagram">.
function renderRaster(spec: RasterSpec): string {
  return `<img src="${esc(spec.asset_ref)}" alt="${esc(spec.alt_text ?? '')}"/>`
}

function renderBarModel(spec: BarModelSpec): string {
  const bars = spec.bars ?? []
  const annotations = spec.annotations ?? []

  const totalBracket = spec.total_bracket ?? null

  // Canvas spans the widest thing drawn: longest bar / annotation, plus the
  // right-hand total brace and its label when present.
  const maxBarUnits = Math.max(1, ...bars.map((b) => b.units))
  const maxAnnUnits = annotations.length
    ? Math.max(...annotations.map((a) => a.to_unit ?? a.from_unit ?? 0))
    : 0
  const spanUnits = Math.max(maxBarUnits, maxAnnUnits, 1)
  let right = LABEL_W + spanUnits * UNIT_W
  if (totalBracket) {
    const braceX = LABEL_W + maxBarUnits * UNIT_W + BRACE_GAP
    const labelX = braceX + BRACE_W + BRACE_LABEL_GAP
    right = Math.max(right, labelX + totalBracket.label.length * CHAR_W + 4)
  }
  const width = right + PAD_RIGHT

  const barsBlockH = bars.length ? bars.length * BAR_H + (bars.length - 1) * ROW_GAP : 0
  const annBlockH = annotations.length * ANN_ROW_H
  const height = PAD_TOP + barsBlockH + (annotations.length ? ANN_GAP + annBlockH : 0) + PAD_TOP

  const out: string[] = [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" ` +
      `width="${width}" height="${height}" role="img" ` +
      `font-family="system-ui, sans-serif" font-size="13">`,
  ]

  let y = PAD_TOP
  for (const bar of bars) {
    const units = bar.units
    const barW = units * UNIT_W
    const textY = y + Math.floor(BAR_H / 2) + 4
    out.push(
      `<text x="${LABEL_W - 8}" y="${textY}" text-anchor="end">${esc(bar.label)}</text>`,
    )
    out.push(
      `<rect x="${LABEL_W}" y="${y}" width="${barW}" height="${BAR_H}" ` +
        `fill="#eef2fb" stroke="#2f5fe0" stroke-width="1.5"/>`,
    )
    for (let u = 1; u < units; u++) {
      const x = LABEL_W + u * UNIT_W
      out.push(
        `<line x1="${x}" y1="${y}" x2="${x}" y2="${y + BAR_H}" ` +
          `stroke="#2f5fe0" stroke-width="0.75"/>`,
      )
    }
    y += BAR_H + ROW_GAP
  }

  // Total brace: a vertical curly brace across all bars → the total.
  if (totalBracket) {
    const yTop = PAD_TOP
    const yBot = PAD_TOP + barsBlockH
    const yMid = Math.floor((yTop + yBot) / 2)
    const bx = LABEL_W + maxBarUnits * UNIT_W + BRACE_GAP
    const cx = bx + BRACE_W
    const d =
      `M ${bx} ${yTop} C ${cx} ${yTop}, ${bx} ${yMid}, ${cx} ${yMid} ` +
      `C ${bx} ${yMid}, ${cx} ${yBot}, ${bx} ${yBot}`
    out.push(`<path d="${d}" fill="none" stroke="#66708a" stroke-width="1.25"/>`)
    out.push(
      `<text x="${cx + BRACE_LABEL_GAP}" y="${yMid + 4}" text-anchor="start" fill="#66708a">${esc(totalBracket.label)}</text>`,
    )
  }

  if (annotations.length) {
    y = PAD_TOP + barsBlockH + ANN_GAP
    for (const ann of annotations) {
      const fromU = ann.from_unit ?? 0
      const toU = ann.to_unit ?? fromU
      const x1 = LABEL_W + fromU * UNIT_W
      const x2 = LABEL_W + toU * UNIT_W
      const mid = Math.floor((x1 + x2) / 2)
      const tickY = y + 8
      out.push(
        `<line x1="${x1}" y1="${tickY}" x2="${x2}" y2="${tickY}" stroke="#66708a" stroke-width="1"/>`,
      )
      out.push(
        `<line x1="${x1}" y1="${tickY - 4}" x2="${x1}" y2="${tickY + 4}" stroke="#66708a" stroke-width="1"/>`,
      )
      out.push(
        `<line x1="${x2}" y1="${tickY - 4}" x2="${x2}" y2="${tickY + 4}" stroke="#66708a" stroke-width="1"/>`,
      )
      out.push(
        `<text x="${mid}" y="${y + ANN_ROW_H - 4}" text-anchor="middle" fill="#66708a">${esc(ann.label)}</text>`,
      )
      y += ANN_ROW_H
    }
  }

  out.push('</svg>')
  return out.join('')
}

// Before-after aid: two stacked stage groups (heading + bars), annotations below,
// and a vertical brace on the invariant person's bar. Mirrors the engine renderer
// in engine/exam_engine/diagram.py (_render_bar_model_before_after). Deterministic.
function renderBarModelBeforeAfter(spec: BarModelBeforeAfterSpec): string {
  const stages = spec.stages ?? []
  const annotations = spec.annotations ?? []
  const totalBracket = spec.total_bracket ?? null

  const allBars = stages.flatMap((s) => s.bars ?? [])
  const maxBarUnits = Math.max(1, ...allBars.map((b) => b.units))
  const bUnits = stages[0]?.bars?.[1]?.units ?? maxBarUnits

  const spanUnits = Math.max(maxBarUnits, 1)
  let right = LABEL_W + spanUnits * UNIT_W

  let braceX = 0
  if (totalBracket) {
    braceX = LABEL_W + bUnits * UNIT_W + BRACE_GAP
    const labelX = braceX + BRACE_W + BRACE_LABEL_GAP
    right = Math.max(right, labelX + totalBracket.label.length * CHAR_W + 4)
  }
  for (const ann of annotations) {
    right = Math.max(right, LABEL_W + ann.label.length * CHAR_W + 4)
  }

  const stageBarsH = 2 * BAR_H + ROW_GAP
  const stageGroupH = STAGE_HEAD_H + stageBarsH
  const annBlockH = annotations.length * ANN_ROW_H
  const height =
    PAD_TOP +
    stageGroupH +
    STAGE_GAP +
    stageGroupH +
    (annotations.length ? ANN_GAP + annBlockH : 0) +
    PAD_TOP
  const width = right + PAD_RIGHT

  const out: string[] = [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" ` +
      `width="${width}" height="${height}" role="img" ` +
      `font-family="system-ui, sans-serif" font-size="13">`,
  ]

  let lastBTop = PAD_TOP
  let lastBBot = PAD_TOP

  let y = PAD_TOP
  for (const stage of stages) {
    out.push(
      `<text x="${LABEL_W - 8}" y="${y + STAGE_HEAD_H - 6}" text-anchor="end" font-weight="bold">${esc(stage.name)}</text>`,
    )
    y += STAGE_HEAD_H
    const bars = stage.bars ?? []
    for (let row = 0; row < bars.length; row++) {
      const bar = bars[row]
      const units = bar.units
      const barW = units * UNIT_W
      const textY = y + Math.floor(BAR_H / 2) + 4
      out.push(
        `<text x="${LABEL_W - 8}" y="${textY}" text-anchor="end">${esc(bar.label)}</text>`,
      )
      out.push(
        `<rect x="${LABEL_W}" y="${y}" width="${barW}" height="${BAR_H}" ` +
          `fill="#eef2fb" stroke="#2f5fe0" stroke-width="1.5"/>`,
      )
      for (let u = 1; u < units; u++) {
        const x = LABEL_W + u * UNIT_W
        out.push(
          `<line x1="${x}" y1="${y}" x2="${x}" y2="${y + BAR_H}" ` +
            `stroke="#2f5fe0" stroke-width="0.75"/>`,
        )
      }
      if (row === 1) {
        lastBTop = y
        lastBBot = y + BAR_H
      }
      y += BAR_H + ROW_GAP
    }
    y += STAGE_GAP - ROW_GAP
  }

  // Total brace on the invariant person's (B's) last bar → its amount.
  if (totalBracket) {
    const yTop = lastBTop
    const yBot = lastBBot
    const yMid = Math.floor((yTop + yBot) / 2)
    const bx = braceX
    const cx = bx + BRACE_W
    const d =
      `M ${bx} ${yTop} C ${cx} ${yTop}, ${bx} ${yMid}, ${cx} ${yMid} ` +
      `C ${bx} ${yMid}, ${cx} ${yBot}, ${bx} ${yBot}`
    out.push(`<path d="${d}" fill="none" stroke="#66708a" stroke-width="1.25"/>`)
    out.push(
      `<text x="${cx + BRACE_LABEL_GAP}" y="${yMid + 4}" text-anchor="start" fill="#66708a">${esc(totalBracket.label)}</text>`,
    )
  }

  // Annotations: plain labelled lines under the stages.
  if (annotations.length) {
    y = PAD_TOP + stageGroupH + STAGE_GAP + stageGroupH + ANN_GAP
    for (const ann of annotations) {
      out.push(
        `<text x="${LABEL_W}" y="${y + ANN_ROW_H - 8}" text-anchor="start" fill="#66708a">${esc(ann.label)}</text>`,
      )
      y += ANN_ROW_H
    }
  }

  out.push('</svg>')
  return out.join('')
}

// shaded_fraction: a shape partitioned into total_parts equal cells with
// shaded_parts filled. rectangle → vertical strips; bar → horizontal strips;
// circle → equal pie sectors. Mirrors _render_shaded_fraction in
// engine/exam_engine/diagram.py. Deterministic (circle rounds trig to ints).
function sfHeader(width: number, height: number): string {
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" ` +
    `width="${width}" height="${height}" role="img" ` +
    `font-family="system-ui, sans-serif" font-size="13">`
  )
}

function renderShadedFraction(spec: ShadedFractionSpec): string {
  if (spec.shape === 'rectangle') return renderSfStrips(spec.total_parts, spec.shaded_parts, false)
  if (spec.shape === 'bar') return renderSfStrips(spec.total_parts, spec.shaded_parts, true)
  if (spec.shape === 'circle') return renderSfCircle(spec.total_parts, spec.shaded_parts)
  return ''
}

function renderSfStrips(totalParts: number, shadedParts: number, horizontal: boolean): string {
  const cell = SF_CELL
  const figW = horizontal ? SF_BAR_W : cell * totalParts
  const figH = horizontal ? cell * totalParts : SF_RECT_H
  const width = figW + 2 * SF_PAD
  const height = figH + 2 * SF_PAD

  const out: string[] = [sfHeader(width, height)]
  for (let i = 0; i < totalParts; i++) {
    const fill = i < shadedParts ? SF_SHADE : SF_EMPTY
    const x = horizontal ? SF_PAD : SF_PAD + i * cell
    const y = horizontal ? SF_PAD + i * cell : SF_PAD
    const cw = horizontal ? figW : cell
    const ch = horizontal ? cell : figH
    out.push(
      `<rect x="${x}" y="${y}" width="${cw}" height="${ch}" ` +
        `fill="${fill}" stroke="${SF_STROKE}" stroke-width="1.5"/>`,
    )
  }
  out.push('</svg>')
  return out.join('')
}

function renderSfCircle(totalParts: number, shadedParts: number): string {
  const r = SF_CIRCLE_R
  const cx = SF_PAD + r
  const cy = SF_PAD + r
  const size = 2 * r + 2 * SF_PAD

  const out: string[] = [sfHeader(size, size)]

  if (totalParts === 1) {
    const fill = shadedParts >= 1 ? SF_SHADE : SF_EMPTY
    out.push(
      `<circle cx="${cx}" cy="${cy}" r="${r}" ` +
        `fill="${fill}" stroke="${SF_STROKE}" stroke-width="1.5"/>`,
    )
  } else {
    const point = (k: number): [number, number] => {
      // Start at the top (12 o'clock), sweep clockwise.
      const angle = (2 * Math.PI * k) / totalParts - Math.PI / 2
      return [Math.round(cx + r * Math.cos(angle)), Math.round(cy + r * Math.sin(angle))]
    }
    for (let i = 0; i < totalParts; i++) {
      const [x1, y1] = point(i)
      const [x2, y2] = point(i + 1)
      const fill = i < shadedParts ? SF_SHADE : SF_EMPTY
      const d = `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 0 1 ${x2} ${y2} Z`
      out.push(`<path d="${d}" fill="${fill}" stroke="${SF_STROKE}" stroke-width="1.5"/>`)
    }
  }
  out.push('</svg>')
  return out.join('')
}

// geometry_figure: a general 2D figure — named points (figure coords) + segments
// (tick marks + length labels) + arcs + angle marks (right-angle square when
// marked) + shaded regions + free labels. Mirrors _render_geometry_figure in
// engine/exam_engine/diagram.py: figure coords are floats scaled uniformly into a
// fixed canvas, every output coordinate rounded via gfRound (Math.floor(v+0.5))
// so this and the Python renderer agree byte-for-byte. Convention: figure coords
// are screen-like (x right, y DOWN); degrees share that y-down frame (positive =
// clockwise on screen). Labelled values stay exact (from the label strings).
const GF_SIZE = 240
const GF_PAD = 28
const GF_ANGLE_R = 18
const GF_RIGHT = 14
const GF_TICK = 6
const GF_TICK_SP = 4
const GF_LABEL_OFF = 13
const GF_STROKE = '#2f5fe0'
const GF_FILL = '#dbe4fb'
const GF_TEXT = '#334155'

// Round half-up — matches Python's math.floor(v + 0.5).
function gfRound(v: number): number {
  return Math.floor(v + 0.5)
}

function gfUnit(dx: number, dy: number): [number, number] {
  const length = Math.hypot(dx, dy)
  if (length === 0) return [0, 0]
  return [dx / length, dy / length]
}

// Points bounding an arc: its endpoints + any cardinal the sweep passes through.
function gfArcExtent(
  cx: number,
  cy: number,
  r: number,
  start: number,
  end: number,
): Array<[number, number]> {
  const lo = Math.min(start, end)
  const hi = Math.max(start, end)
  const pts: Array<[number, number]> = []
  for (const deg of [start, end, 0, 90, 180, 270, 360]) {
    if ((lo <= deg && deg <= hi) || deg === start || deg === end) {
      const rad = (deg * Math.PI) / 180
      pts.push([cx + r * Math.cos(rad), cy + r * Math.sin(rad)])
    }
  }
  return pts
}

function gfHeader(width: number, height: number): string {
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" ` +
    `width="${width}" height="${height}" role="img" ` +
    `font-family="system-ui, sans-serif" font-size="13">`
  )
}

function renderGeometryFigure(spec: GeometryFigureSpec): string {
  const points = spec.points ?? []
  const pmap = new Map<string, [number, number]>(points.map((p) => [p.id, [p.x, p.y]]))
  const segments = spec.segments ?? []
  const arcs = spec.arcs ?? []
  const angles = spec.angles ?? []
  const shaded = spec.shaded ?? []
  const labels = spec.labels ?? []

  const at = (id: string): [number, number] => pmap.get(id) ?? [0, 0]

  // Bounding box over points + arc extents.
  const xs: number[] = points.map((p) => p.x)
  const ys: number[] = points.map((p) => p.y)
  for (const arc of arcs) {
    const [cx, cy] = at(arc.center)
    xs.push(cx)
    ys.push(cy)
    for (const [ax, ay] of gfArcExtent(cx, cy, arc.radius, arc.start_deg, arc.end_deg)) {
      xs.push(ax)
      ys.push(ay)
    }
  }

  const minx = Math.min(...xs)
  const maxx = Math.max(...xs)
  const miny = Math.min(...ys)
  const maxy = Math.max(...ys)
  const w = maxx - minx
  const h = maxy - miny
  let denom = Math.max(w, h)
  if (denom <= 0) denom = 1
  const scale = GF_SIZE / denom

  const tx = (x: number): number => gfRound(GF_PAD + (x - minx) * scale)
  const ty = (y: number): number => gfRound(GF_PAD + (y - miny) * scale)

  const width = gfRound(w * scale) + 2 * GF_PAD
  const height = gfRound(h * scale) + 2 * GF_PAD

  const out: string[] = [gfHeader(width, height)]

  // Shaded regions (behind the strokes). Trace each boundary as one closed
  // <path>: edges are straight by default, but an entry in the region's arcs
  // (keyed by its from→to point pair) turns that edge into a circular arc, so a
  // polygon-minus-circle region (square minus quarter circle, crescent, annulus)
  // fills visually. Mirrors the shaded loop in engine/exam_engine/diagram.py.
  for (const region of shaded) {
    const boundary = region.boundary ?? []
    const pts = boundary.map((id) => [tx(at(id)[0]), ty(at(id)[1])] as [number, number])
    if (pts.length < 2) continue
    const arcEdges = new Map<string, GeometryShadedArc>()
    for (const a of region.arcs ?? []) arcEdges.set(`${a.from}->${a.to}`, a)
    const edge = (arc: GeometryShadedArc | undefined, pt: [number, number]): string => {
      if (!arc) return `L ${pt[0]} ${pt[1]}`
      const rr = gfRound(arc.radius * scale)
      const large = arc.large ?? 0
      const sweep = arc.sweep ?? 0
      return `A ${rr} ${rr} 0 ${large} ${sweep} ${pt[0]} ${pt[1]}`
    }
    const parts = [`M ${pts[0][0]} ${pts[0][1]}`]
    for (let i = 1; i < pts.length; i++) {
      parts.push(edge(arcEdges.get(`${boundary[i - 1]}->${boundary[i]}`), pts[i]))
    }
    const closing = `${boundary[boundary.length - 1]}->${boundary[0]}`
    if (arcEdges.has(closing)) parts.push(edge(arcEdges.get(closing), pts[0]))
    const d = parts.join(' ') + ' Z'
    out.push(`<path d="${d}" fill="${GF_FILL}" stroke="none"/>`)
  }

  // Segments (edges + tick marks + length labels).
  for (const seg of segments) {
    const [ax, ay] = at(seg.from)
    const [bx, by] = at(seg.to)
    const x1 = tx(ax)
    const y1 = ty(ay)
    const x2 = tx(bx)
    const y2 = ty(by)
    out.push(
      `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${GF_STROKE}" stroke-width="2"/>`,
    )
    const mx = (x1 + x2) / 2
    const my = (y1 + y2) / 2
    const [ux, uy] = gfUnit(x2 - x1, y2 - y1)
    const nx = -uy
    const ny = ux
    const ticks = seg.ticks ?? 0
    for (let i = 0; i < ticks; i++) {
      const off = (i - (ticks - 1) / 2) * GF_TICK_SP
      const cxp = mx + ux * off
      const cyp = my + uy * off
      out.push(
        `<line x1="${gfRound(cxp - nx * GF_TICK)}" y1="${gfRound(cyp - ny * GF_TICK)}" ` +
          `x2="${gfRound(cxp + nx * GF_TICK)}" y2="${gfRound(cyp + ny * GF_TICK)}" ` +
          `stroke="${GF_STROKE}" stroke-width="1.5"/>`,
      )
    }
    if (seg.label != null) {
      const lx = gfRound(mx + nx * GF_LABEL_OFF)
      const ly = gfRound(my + ny * GF_LABEL_OFF + 4)
      out.push(
        `<text x="${lx}" y="${ly}" text-anchor="middle" fill="${GF_TEXT}">${esc(seg.label)}</text>`,
      )
    }
  }

  // Arcs (whole/semi/quarter circles).
  for (const arc of arcs) {
    const [cx, cy] = at(arc.center)
    const r = arc.radius
    const start = arc.start_deg
    const end = arc.end_deg
    const p1x = tx(cx + r * Math.cos((start * Math.PI) / 180))
    const p1y = ty(cy + r * Math.sin((start * Math.PI) / 180))
    const p2x = tx(cx + r * Math.cos((end * Math.PI) / 180))
    const p2y = ty(cy + r * Math.sin((end * Math.PI) / 180))
    const rr = gfRound(r * scale)
    const large = Math.abs(end - start) > 180 ? 1 : 0
    const sweep = end >= start ? 1 : 0
    out.push(
      `<path d="M ${p1x} ${p1y} A ${rr} ${rr} 0 ${large} ${sweep} ${p2x} ${p2y}" ` +
        `fill="none" stroke="${GF_STROKE}" stroke-width="2"/>`,
    )
    if (arc.label != null) {
      const mid = (((start + end) / 2) * Math.PI) / 180
      const lx = gfRound(tx(cx + r * Math.cos(mid)) + Math.cos(mid) * 12)
      const ly = gfRound(ty(cy + r * Math.sin(mid)) + Math.sin(mid) * 12 + 4)
      out.push(
        `<text x="${lx}" y="${ly}" text-anchor="middle" fill="${GF_TEXT}">${esc(arc.label)}</text>`,
      )
    }
  }

  // Angle marks (small arc, or a square for right angles).
  for (const ang of angles) {
    const [vx, vy] = at(ang.at)
    const [ax, ay] = at(ang.from)
    const [bx, by] = at(ang.to)
    const vX = tx(vx)
    const vY = ty(vy)
    const [dax, day] = gfUnit(tx(ax) - vX, ty(ay) - vY)
    const [dbx, dby] = gfUnit(tx(bx) - vX, ty(by) - vY)
    if (ang.right) {
      const s = GF_RIGHT
      const p1 = [gfRound(vX + dax * s), gfRound(vY + day * s)]
      const p2 = [gfRound(vX + (dax + dbx) * s), gfRound(vY + (day + dby) * s)]
      const p3 = [gfRound(vX + dbx * s), gfRound(vY + dby * s)]
      out.push(
        `<polyline points="${p1[0]},${p1[1]} ${p2[0]},${p2[1]} ${p3[0]},${p3[1]}" ` +
          `fill="none" stroke="${GF_STROKE}" stroke-width="1.5"/>`,
      )
    } else {
      const rr = GF_ANGLE_R
      const p1x = gfRound(vX + dax * rr)
      const p1y = gfRound(vY + day * rr)
      const p2x = gfRound(vX + dbx * rr)
      const p2y = gfRound(vY + dby * rr)
      const a1 = (Math.atan2(day, dax) * 180) / Math.PI
      const a2 = (Math.atan2(dby, dbx) * 180) / Math.PI
      const diff = (((a2 - a1 + 180) % 360) + 360) % 360 - 180
      const sweep = diff > 0 ? 1 : 0
      out.push(
        `<path d="M ${p1x} ${p1y} A ${rr} ${rr} 0 0 ${sweep} ${p2x} ${p2y}" ` +
          `fill="none" stroke="${GF_STROKE}" stroke-width="1.5"/>`,
      )
      if (ang.value_deg != null && !ang.unknown) {
        let [bisx, bisy] = gfUnit(dax + dbx, day + dby)
        if (bisx === 0 && bisy === 0) {
          bisx = -day
          bisy = dax
        }
        const lx = gfRound(vX + bisx * (rr + 12))
        const ly = gfRound(vY + bisy * (rr + 12) + 4)
        out.push(
          `<text x="${lx}" y="${ly}" text-anchor="middle" fill="${GF_TEXT}">${esc(String(ang.value_deg))}°</text>`,
        )
      }
    }
  }

  // Free text labels.
  for (const lab of labels) {
    const [px, py] = at(lab.at)
    out.push(`<text x="${tx(px) + 6}" y="${ty(py) - 6}" fill="${GF_TEXT}">${esc(lab.text)}</text>`)
  }

  out.push('</svg>')
  return out.join('')
}
