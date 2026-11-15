// P8a: what the one-click generator filled, shown once as a banner in the editor, and the
// count of placeholders the teacher still has to write (a mirror of the engine's
// `paper.unfilled_placeholders`).
import { writable } from 'svelte/store'
import type { DocJSON, DocNode } from './doc'
import type { PaperReport } from './docsApi'

/** The report of the paper just generated, for the editor that opens it next. */
export const lastReport = writable<{ docId: string; report: PaperReport } | null>(null)

const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`

/** One honest paragraph: what came from the blueprints, and what is left to write. */
export function reportSummary(r: PaperReport): string {
  const slots = r.filled + r.placeholders
  const bits = [`Filled ${r.filled} of ${slots} questions from the question generator.`]
  if (r.placeholders) {
    bits.push(
      `${plural(r.placeholders, 'placeholder')} (${plural(r.placeholder_marks, 'mark')}) left for you to write or replace.`,
    )
  }
  for (const s of r.sections) {
    if (s.multipart && s.stand_ins) {
      bits.push(
        `${s.title} has ${plural(s.multipart, 'multi-part question')}; ${plural(s.stand_ins, 'single-part question')} ${s.stand_ins === 1 ? 'stands' : 'stand'} in for the rest.`,
      )
    } else if (s.stand_ins) {
      bits.push(
        `${s.title} uses ${plural(s.stand_ins, 'single-part question')} in place of multi-part ones.`,
      )
    }
    if (s.mode === 'mcq' && s.placeholders) {
      bits.push(
        `${s.title}: ${plural(s.placeholders, 'multiple-choice question')} still to write (not enough convertible questions yet).`,
      )
    }
  }
  return bits.join(' ')
}

/** Any non-blank text, or an image / equation, anywhere in these nodes (parts included). */
export function hasContent(nodes: DocNode[] | undefined): boolean {
  return (nodes ?? []).some(
    (n) =>
      (n.type === 'text' && !!n.text?.trim()) ||
      n.type === 'image' ||
      n.type === 'math' ||
      hasContent(n.content),
  )
}

/** Placeholders the teacher hasn't written yet: nothing in the stem or any part (engine mirror). */
export function unfilledPlaceholders(doc: DocJSON): number {
  return (doc.content ?? []).filter((n) => {
    const slot = n.attrs?.slot as { placeholder?: boolean } | null | undefined
    return n.type === 'freeformQuestion' && !!slot?.placeholder && !hasContent(n.content)
  }).length
}
