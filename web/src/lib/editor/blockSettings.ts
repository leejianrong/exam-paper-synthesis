// Section and cover settings live in the side panel (EXA-164). On the page the block is a compact
// header or card: a click selects it (the panel shows its settings), and its Edit button, or
// Alt+Enter with the block selected, opens the panel at its first field.
import type { Editor } from '@tiptap/core'
import type { Node as PMNode } from '@tiptap/pm/model'
import { NodeSelection, type EditorState, type Transaction } from '@tiptap/pm/state'
import { keyLabel } from '../keys'

export const SETTINGS_KEY = 'Alt+Enter'

/** Opens the settings of the block at `pos` in the side panel. */
export type OpenSettings = (pos: number) => void

/** The Edit button a section header or cover card carries. */
export function editButton(name: string, open: () => void): HTMLButtonElement {
  const btn = document.createElement('button')
  btn.type = 'button'
  btn.className = 'block-edit'
  btn.textContent = 'Edit'
  btn.setAttribute('aria-label', `Edit ${name}`)
  btn.title = `Edit ${name} (${keyLabel(SETTINGS_KEY)})`
  btn.addEventListener('click', (e) => {
    e.preventDefault()
    open()
  })
  return btn
}

/** Alt+Enter on a selected block of this type: open its settings. */
export function settingsShortcut(editor: Editor, type: string, open: OpenSettings | null): boolean {
  const sel = editor.state.selection
  if (!open || !(sel instanceof NodeSelection) || sel.node.type.name !== type) return false
  open(sel.from)
  return true
}

/** A section (the n-th in the paper) or the cover, with its attrs: what the side panel edits. */
export type SettingsBlock =
  | { kind: 'section'; index: number; attrs: Record<string, unknown> }
  | { kind: 'cover'; attrs: Record<string, unknown> }

/** The selected top-level section or cover, else null. */
export function selectedSettingsBlock(state: EditorState): SettingsBlock | null {
  const sel = state.selection
  if (!(sel instanceof NodeSelection) || sel.$from.depth !== 0) return null
  const name = sel.node.type.name
  if (name === 'coverPage') return { kind: 'cover', attrs: sel.node.attrs }
  if (name !== 'section') return null
  let index = 0
  state.doc.forEach((child, offset) => {
    if (child.type.name === 'section' && offset < sel.from) index += 1
  })
  return { kind: 'section', index, attrs: sel.node.attrs }
}

/** Where that block starts now, or null when it is gone. */
export function settingsBlockPos(doc: PMNode, block: SettingsBlock): number | null {
  let seen = -1
  let at: number | null = null
  doc.forEach((child, offset) => {
    if (at !== null) return
    if (block.kind === 'cover' && child.type.name === 'coverPage') at = offset
    if (block.kind === 'section' && child.type.name === 'section' && ++seen === block.index) at = offset
  })
  return at
}

/** Set attrs on the block at `pos` and keep it selected, so the panel stays on it. */
export function settingsTransaction(state: EditorState, pos: number, attrs: Record<string, unknown>): Transaction {
  const node = state.doc.nodeAt(pos)
  const tr = state.tr.setNodeMarkup(pos, undefined, { ...node?.attrs, ...attrs })
  return tr.setSelection(NodeSelection.create(tr.doc, pos))
}

/** Node-view events the editor must leave alone: the Edit button's. */
export function isEditButton(event: Event): boolean {
  return !!(event.target as HTMLElement | null)?.closest?.('.block-edit')
}
