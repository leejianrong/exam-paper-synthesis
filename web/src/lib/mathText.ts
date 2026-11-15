/** Text and `\( … \)` formulas, in order (the formulas without their delimiters). */
export function splitMath(text: string): Array<{ math: boolean; value: string }> {
  const out: Array<{ math: boolean; value: string }> = []
  const re = /\\\((.+?)\\\)/gs
  let at = 0
  for (const m of text.matchAll(re)) {
    if (m.index > at) out.push({ math: false, value: text.slice(at, m.index) })
    out.push({ math: true, value: m[1].trim() })
    at = m.index + m[0].length
  }
  if (at < text.length) out.push({ math: false, value: text.slice(at) })
  return out
}
