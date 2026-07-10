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
  return ''
}

function renderBarModel(spec) {
  const bars = spec.bars ?? []
  const annotations = spec.annotations ?? []

  const maxUnits = Math.max(1, ...bars.map((b) => b.units))
  const contentW = maxUnits * UNIT_W
  const width = LABEL_W + contentW + PAD_RIGHT

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
