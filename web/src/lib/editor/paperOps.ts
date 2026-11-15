// P8d: keep / swap / lock on a generated paper. The server computes a swap or a
// "regenerate unlocked" on the saved paper and saves the result; the editor then takes the
// blocks that changed (one undoable step, the rest of the page and the scroll untouched).

import type { Editor } from '@tiptap/core'
import { cleanNode, type DocJSON, type DocNode } from './doc'
import type { RegenerateReport, SwapReport } from './docsApi'

/** Does the paper have positions the generator filled (so "Regenerate unlocked" applies)? */
export function hasGeneratedSlots(doc: DocJSON): boolean {
  return (doc.content ?? []).some(
    (n) => (n.type === 'templatedQuestion' || n.type === 'freeformQuestion') && !!n.attrs?.slot,
  )
}

const same = (a: DocNode, b: DocNode) => JSON.stringify(cleanNode(a)) === JSON.stringify(cleanNode(b))

/** Make the editor's document `next`, replacing only the top-level blocks that differ. */
export function applyServerContent(editor: Editor, next: DocJSON): number {
  const current = editor.getJSON() as DocJSON
  const blocks = next.content ?? []
  if ((current.content ?? []).length !== blocks.length) {
    editor.commands.setContent(next, { emitUpdate: false })
    return blocks.length
  }
  const { state } = editor
  const tr = state.tr
  let changed = 0
  // Back to front, so the positions still to visit don't move.
  const starts: number[] = []
  state.doc.forEach((_node, offset) => starts.push(offset))
  for (let i = blocks.length - 1; i >= 0; i--) {
    if (same(current.content[i], blocks[i])) continue
    const from = starts[i]
    const to = from + state.doc.child(i).nodeSize
    tr.replaceWith(from, to, state.schema.nodeFromJSON(blocks[i]))
    changed++
  }
  if (changed) editor.view.dispatch(tr)
  return changed
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
