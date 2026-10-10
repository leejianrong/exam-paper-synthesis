import type { Answer } from './types'

/** Plain-text rendering of a typed answer (the web mirror of the engine's _fmt_answer). */
export function fmtAnswer(a: Answer | undefined): string {
  if (!a) return ''
  switch (a.type) {
    case 'quantity':
    case 'decimal':
    case 'integer': {
      const u = a.unit ?? ''
      // Money renders at exactly 2 dp when it is a decimal amount (KAN-309).
      const shown = u === '$' && a.type === 'decimal' ? Number(a.value).toFixed(2) : `${a.value}`
      if (u === '$') return `$${shown}`
      return u ? `${shown} ${u}` : `${shown}`
    }
    case 'fraction':
      return `${a.numerator}/${a.denominator}`
    case 'ratio':
      return (a.parts ?? []).join(' : ')
    case 'set':
      return (a.values ?? []).join(', ')
    case 'text':
      return a.text ?? ''
    case 'choice': {
      const hit = (a.options ?? []).find((o) => o.label === a.correct)
      return hit?.text ? `${a.correct}. ${hit.text}` : `${a.correct ?? ''}`
    }
    case 'expression': {
      const body = (a.terms ?? [])
        .map((t, i) => {
          const sym = t.symbol ?? ''
          const pow = sym && (t.power ?? 1) > 1 ? `^${t.power}` : ''
          const mag = Math.abs(t.coefficient)
          const coef = sym && mag === 1 ? '' : `${mag}`
          const sign = t.coefficient < 0 ? (i === 0 ? '-' : ' - ') : i === 0 ? '' : ' + '
          return `${sign}${coef}${sym}${pow}`
        })
        .join('')
      const u = a.unit ?? ''
      return u === '$' ? `$${body}` : u ? `${body} ${u}` : body
    }
    default:
      return JSON.stringify(a)
  }
}
