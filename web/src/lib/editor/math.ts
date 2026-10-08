// KaTeX in the editor (W2b): typeset one LaTeX string into a host element. The stylesheet
// (KaTeX fonts + print CSS) lives in a shadow root per formula so it cannot leak into the
// app; the script is the same bundle the PDF uses, installed once (fragments.ts).

import { loadFragmentAssets } from './fragments'

interface Katex {
  render(latex: string, el: HTMLElement, opts: Record<string, unknown>): void
}

export interface MathResult {
  /** False when KaTeX rejected the formula (the message says why). */
  ok: boolean
  error?: string
}

/**
 * Typeset `latex` into `host`'s shadow root. Resolves `{ok:false}` for a formula KaTeX
 * cannot parse (and shows the raw source), and `{ok:true}` with the raw source shown when
 * KaTeX is unavailable (offline, tests) — never throws.
 */
export async function mountMath(host: HTMLElement, latex: string): Promise<MathResult> {
  const root = host.shadowRoot ?? host.attachShadow({ mode: 'open' })
  let target = root.querySelector<HTMLElement>('.m')
  if (!target) {
    target = document.createElement('span')
    target.className = 'm'
    root.append(target)
  }
  target.textContent = latex
  try {
    const assets = await loadFragmentAssets()
    if (!root.querySelector('style') && !root.adoptedStyleSheets?.length) assets.applyTo(root)
  } catch {
    return { ok: true }
  }
  const katex = (globalThis as { katex?: Katex }).katex
  if (!katex) return { ok: true }
  try {
    katex.render(latex, target, { throwOnError: true, displayMode: false, trust: false })
    return { ok: true }
  } catch (e) {
    target.textContent = latex
    return { ok: false, error: e instanceof Error ? e.message.replace(/^KaTeX parse error: /, '') : String(e) }
  }
}

/** Typeset every `.math-host[data-latex]` under `el` (read-only views of saved text). */
export function mountMathIn(el: HTMLElement): void {
  for (const host of el.querySelectorAll<HTMLElement>('.math-host[data-latex]')) {
    void mountMath(host, host.dataset.latex ?? '')
  }
}

/** Svelte action: keep read-only `{@html}` math typeset as the markup changes. */
// eslint-disable-next-line @typescript-eslint/no-unused-vars -- the parameter only re-runs the action
export function typesetMath(node: HTMLElement, _html?: string) {
  mountMathIn(node)
  return {
    update() {
      queueMicrotask(() => mountMathIn(node))
    },
  }
}

/** The eight forms a P5–P6 paper needs, offered as one-click snippets. */
export const MATH_SNIPPETS: Array<{ label: string; latex: string }> = [
  { label: 'Fraction', latex: '\\frac{3}{4}' },
  { label: 'Mixed number', latex: '2\\frac{1}{3}' },
  { label: 'Ratio', latex: '3 : 4' },
  { label: 'Percent', latex: '25\\%' },
  { label: 'Multiply', latex: '\\times' },
  { label: 'Divide', latex: '\\div' },
  { label: 'Square', latex: 'x^{2}' },
  { label: 'Pi', latex: '\\pi' },
]
