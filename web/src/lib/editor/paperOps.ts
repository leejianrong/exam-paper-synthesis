// P8d: keep / swap / lock on a generated paper. The server computes a swap or a
// "regenerate unlocked" on the saved paper and saves the result; the editor then takes the
// blocks that changed (one undoable step, the rest of the page and the scroll untouched).

import type { Editor } from '@tiptap/core'
import { cleanNode, type DocJSON, type DocNode } from './doc'
import type { RegenerateReport, SwapReport } from './docsApi'

/** A question "Regenerate unlocked" may refill, and that therefore shows swap and Lock: a
 *  generated (not bank) templated question, with or without a slot, or a generator placeholder.
 *  Mirrors the engine's `paper_swap._refillable` (less the lock). */
export function isGeneratedPosition(n: DocNode): boolean {
  if (n.type === 'templatedQuestion') {
    const q = n.attrs?.question as { source_type?: string; blueprint_code?: string } | null
    return q?.source_type === 'generated' && !!q.blueprint_code
  }
  const slot = n.attrs?.slot as { placeholder?: boolean } | null | undefined
  return n.type === 'freeformQuestion' && !!slot?.placeholder
}

/** Does the paper have anything "Regenerate unlocked" would refill? */
export function hasGeneratedSlots(doc: DocJSON): boolean {
  return (doc.content ?? []).some(isGeneratedPosition)
}

/** JSON with object keys sorted: the editor and the server order a node's attributes differently. */
function canonical(v: unknown): string {
  if (Array.isArray(v)) return `[${v.map(canonical).join(',')}]`
  if (v && typeof v === 'object') {
    const o = v as Record<string, unknown>
    return `{${Object.keys(o)
      .filter((k) => o[k] !== undefined)
      .sort()
      .map((k) => `${JSON.stringify(k)}:${canonical(o[k])}`)
      .join(',')}}`
  }
  return JSON.stringify(v)
}

const same = (a: DocNode, b: DocNode) => canonical(cleanNode(a)) === canonical(cleanNode(b))

/** Take the server's changes: `sent` is the document the server worked on and `next` what it
 *  saved. Only the question blocks the server changed (next ≠ sent, matched by block id) are
 *  replaced in the editor, so anything else — even a change made while the request was out —
 *  is kept. If the questions don't line up (never the case for a swap), the server's document
 *  is taken whole. Returns how many blocks were replaced. */
export function applyServerContent(editor: Editor, sent: DocJSON, next: DocJSON): number {
  const before = byId(sent)
  const after = byId(next)
  const sameIds = before.size === after.size && [...after.keys()].every((k) => before.has(k))
  if (!sameIds) {
    editor.commands.setContent(next, { emitUpdate: false })
    return after.size
  }
  const changed = new Map<string, DocNode>()
  for (const [id, node] of after) if (!same(before.get(id) as DocNode, node)) changed.set(id, node)
  if (!changed.size) return 0
  const { state } = editor
  const targets: Array<{ from: number; to: number; node: DocNode }> = []
  state.doc.forEach((child, offset) => {
    if (!QUESTION_TYPES.includes(child.type.name)) return
    const node = changed.get(child.attrs.block_id as string)
    if (node) targets.push({ from: offset, to: offset + child.nodeSize, node })
  })
  const tr = state.tr
  // Back to front, so the positions still to visit don't move.
  for (const t of targets.reverse()) tr.replaceWith(t.from, t.to, state.schema.nodeFromJSON(t.node))
  editor.view.dispatch(tr)
  return targets.length
}

const QUESTION_TYPES = ['templatedQuestion', 'freeformQuestion']

/** Question blocks by id (a swap or regenerate only ever changes question blocks, in place). */
function byId(doc: DocJSON): Map<string, DocNode> {
  const out = new Map<string, DocNode>()
  for (const n of doc.content ?? []) {
    const id = n.attrs?.block_id
    if (typeof id === 'string' && QUESTION_TYPES.includes(n.type)) out.set(id, n)
  }
  return out
}

/** One line for the page after a swap. */
export function swapNotice(r: SwapReport): string {
  if (r.placeholder) return `Placeholder ready: write your own ${r.marks}-mark question there.`
  return `Swapped in a ${r.marks}-mark ${r.topic ?? ''} question.`.replace('  ', ' ')
}

/** One line for the page after "Regenerate unlocked". */
export function regenerateNotice(r: RegenerateReport): string {
  const bits = [`Regenerated ${r.replaced} question${r.replaced === 1 ? '' : 's'}`]
  if (r.kept) bits.push(`kept ${r.kept} locked or written by you`)
  if (r.placeholders) bits.push(`${r.placeholders} left as placeholders`)
  return bits.join('; ') + '.'
}
