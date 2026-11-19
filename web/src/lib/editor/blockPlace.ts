// Where a question block stands in the paper, for its controls (EXA-161): its printed number
// (the block's accessible name), whether the editor's selection is on or in it while the
// editor has focus (its pill shows), and whether it can move up or down.
import type { Editor } from '@tiptap/core'
import { paperSettings } from './paperSettings'
import { numberFrom } from './layout'

export interface BlockPlace {
  number: number | null
  selected: boolean
  canMoveUp: boolean
  canMoveDown: boolean
}

export const NOWHERE: BlockPlace = { number: null, selected: false, canMoveUp: false, canMoveDown: false }

const QUESTIONS = ['templatedQuestion', 'freeformQuestion']

export function readPlace(editor: Editor, pos: number | undefined, start: number): BlockPlace {
  if (typeof pos !== 'number') return NOWHERE
  try {
    const { doc, selection } = editor.state
    const node = doc.nodeAt(pos)
    if (!node) return NOWHERE
    const index = doc.resolve(pos).index(0)
    let before = 0
    for (let i = 0; i < index; i++) if (QUESTIONS.includes(doc.child(i).type.name)) before++
    const end = pos + node.nodeSize
    const inside = selection.from >= pos && selection.to <= end
    return {
      number: start + before,
      selected: inside && editor.view.hasFocus(),
      canMoveUp: index > 0,
      canMoveDown: index < doc.childCount - 1,
    }
  } catch {
    return NOWHERE // the node view is being torn down
  }
}

const same = (a: BlockPlace, b: BlockPlace) =>
  a.number === b.number && a.selected === b.selected && a.canMoveUp === b.canMoveUp && a.canMoveDown === b.canMoveDown

/** Calls `apply` with the block's place now and whenever it changes. Returns a stop function. */
export function trackPlace(
  editor: Editor,
  getPos: () => number | undefined,
  apply: (p: BlockPlace) => void,
): () => void {
  let start = 1
  let last: BlockPlace | null = null
  const refresh = () => {
    const p = readPlace(editor, getPos(), start)
    if (!last || !same(last, p)) {
      last = p
      apply(p)
    }
  }
  const stopSettings = paperSettings.subscribe((s) => {
    start = numberFrom(s)
    refresh()
  })
  // After ProseMirror has placed the node (getPos is not ready while the view is built).
  queueMicrotask(refresh)
  editor.on('transaction', refresh)
  editor.on('focus', refresh)
  editor.on('blur', refresh)
  return () => {
    stopSettings()
    editor.off('transaction', refresh)
    editor.off('focus', refresh)
    editor.off('blur', refresh)
  }
}
