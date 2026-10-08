// Embedding engine-rendered question HTML (W1d). The server renders the same markup the
// PDF uses; here we cache it, share one stylesheet across shadow roots, and typeset math.

import { fetchFragmentAssets, renderQuestionHtml } from '../api'
import type { Question } from '../types'

const htmlCache = new Map<string, Promise<string>>()

/** Rendered HTML for a question, cached by content so reorders/re-mounts don't refetch. */
export function renderQuestion(
  q: Question,
  mode: 'student' | 'key',
  number: number | null,
): Promise<string> {
  const key = `${mode}|${number ?? ''}|${JSON.stringify(q)}`
  let hit = htmlCache.get(key)
  if (!hit) {
    hit = renderQuestionHtml(q, mode, number)
    htmlCache.set(key, hit)
    hit.catch(() => htmlCache.delete(key)) // never cache a failure
  }
  return hit
}

export interface FragmentAssets {
  /** Attach the shared stylesheet to a shadow root (adopted sheet, <style> as fallback). */
  applyTo(root: ShadowRoot): void
}

let assetsPromise: Promise<FragmentAssets> | null = null

/** Fetch the stylesheet + KaTeX once per page load. */
export function loadFragmentAssets(): Promise<FragmentAssets> {
  assetsPromise ??= fetchFragmentAssets()
    .then(({ css, js }) => {
      installKatex(js)
      let sheet: CSSStyleSheet | null = null
      if ('adoptedStyleSheets' in Document.prototype && typeof CSSStyleSheet !== 'undefined') {
        try {
          sheet = new CSSStyleSheet()
          sheet.replaceSync(css)
        } catch {
          sheet = null
        }
      }
      return {
        applyTo(root: ShadowRoot) {
          if (sheet) {
            root.adoptedStyleSheets = [sheet]
          } else {
            const style = document.createElement('style')
            style.textContent = css
            root.prepend(style)
          }
        },
      }
    })
    .catch((e) => {
      assetsPromise = null // allow a retry on the next fragment
      throw e
    })
  return assetsPromise
}

function installKatex(js: string): void {
  if ((globalThis as { renderMathInElement?: unknown }).renderMathInElement) return
  const script = document.createElement('script')
  script.textContent = js
  document.head.appendChild(script)
}

/** Typeset `\( … \)` / `\[ … \]` math inside `el` (a no-op where KaTeX is unavailable, e.g. jsdom). */
export function typeset(el: HTMLElement): void {
  const render = (
    globalThis as {
      renderMathInElement?: (el: HTMLElement, opts: Record<string, unknown>) => void
    }
  ).renderMathInElement
  render?.(el, {
    delimiters: [
      { left: '\\(', right: '\\)', display: false },
      { left: '\\[', right: '\\]', display: true },
    ],
    throwOnError: false,
  })
}
