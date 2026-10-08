// A tiny request channel between the math nodes (in any editor: the page or an answer) and
// the one popover the page mounts. The node says what it holds and how to apply a change.

import { writable } from 'svelte/store'

export interface MathRequest {
  latex: string
  /** Called with the new LaTeX, or `null` to remove the formula. */
  apply: (latex: string | null) => void
}

export const mathRequest = writable<MathRequest | null>(null)

export function openMathEditor(request: MathRequest): void {
  mathRequest.set(request)
}

export function closeMathEditor(): void {
  mathRequest.set(null)
}
