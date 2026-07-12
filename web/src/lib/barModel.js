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

function esc(text) {
  return String(text)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
}

/** Render a diagram spec to an inline <svg> string. Returns '' for unknowns. */
export function renderDiagram(spec) {
  if (!spec) return ''
  if (spec.type === 'bar_model') return renderBarModel(spec)
  if (spec.type === 'bar_model_before_after') return renderBarModelBeforeAfter(spec)
  return ''
}

function renderBarModel(spec) {
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

  const out = [
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
function renderBarModelBeforeAfter(spec) {
  const stages = spec.stages ?? []
  const annotations = spec.annotations ?? []
  const totalBracket = spec.total_bracket ?? null

  const allBars = stages.flatMap((s) => s.bars ?? [])
  const maxBarUnits = Math.max(1, ...allBars.map((b) => b.units))
  const bUnits = stages[0]?.bars?.[1]?.units ?? maxBarUnits

  const spanUnits = Math.max(maxBarUnits, 1)
  let right = LABEL_W + spanUnits * UNIT_W

  let braceX = null
  let labelX = null
  if (totalBracket) {
    braceX = LABEL_W + bUnits * UNIT_W + BRACE_GAP
    labelX = braceX + BRACE_W + BRACE_LABEL_GAP
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

  const out = [
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
