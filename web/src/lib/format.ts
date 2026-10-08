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
    default:
      return JSON.stringify(a)
  }
}
