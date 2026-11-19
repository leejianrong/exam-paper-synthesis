// A whole block selected (one click on a cover, a section, a question or an image) must never be
// replaced by what comes next (EXA-129): the toolbar's Section / Blank page / Page break went
// over it, and so did the first keystroke or a paste, so one click on the cover and a typed
// letter wiped the cover. Toolbar inserts go after the selected block's top-level block;
// typing, Enter or a paste with a top-level block selected start after it. Backspace / Delete
// still delete a selected block on purpose. A block selected *inside* a question (a free-form
// part, an image in its body) keeps the editor's default, so a question is never split.

import { Extension, type Editor, type JSONContent } from '@tiptap/core'
import {
  NodeSelection,
  Plugin,
  PluginKey,
  TextSelection,
  type EditorState,
  type Transaction,
} from '@tiptap/pm/state'

/** The selected block when it is a top-level block of the paper (a direct child of the doc). */
function selectedTopBlock(state: EditorState): NodeSelection | null {
  const sel = state.selection
  return sel instanceof NodeSelection && sel.node.isBlock && sel.$from.depth === 0 ? sel : null
}

/** Where a block goes when the toolbar inserts one with a block selected: after the selected
 *  top-level block (a nested selection counts as its question), else null (insert at the caret). */
function afterSelectedBlock(state: EditorState): number | null {
  const sel = state.selection
  if (!(sel instanceof NodeSelection) || !sel.node.isBlock) return null
  return sel.$from.depth === 0 ? sel.to : sel.$from.after(1)
}

/** A transaction that adds an empty paragraph right after the selected top-level block and puts
 *  the caret in it (or in the empty paragraph already there). */
function caretAfter(state: EditorState, sel: NodeSelection): Transaction {
  const tr = state.tr
  const after = sel.to
  const next = state.doc.resolve(after).nodeAfter
  if (!next || next.type.name !== 'paragraph' || next.content.size > 0) {
    tr.insert(after, state.schema.nodes.paragraph.create())
  }
  return tr.setSelection(TextSelection.create(tr.doc, after + 1))
}

/** Insert a block: after a selected block (never over it, never inside a question), else as
 *  `insertContent` would at the caret. */
export function insertBlockSafely(editor: Editor, content: JSONContent): void {
  const at = afterSelectedBlock(editor.state)
  if (at !== null) {
    editor.chain().insertContentAt(at, content).run()
    editor.view.focus()
  } else {
    editor.chain().focus().insertContent(content).run()
  }
}

export const BlockSelectionGuard = Extension.create({
  name: 'blockSelectionGuard',
  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey('blockSelectionGuard'),
        props: {
          handleTextInput(view, _from, _to, text) {
            const sel = selectedTopBlock(view.state)
            if (!sel) return false
            view.dispatch(caretAfter(view.state, sel).insertText(text))
            return true
          },
          handleKeyDown(view, event) {
            // Alt+Enter on a selected section or cover opens its settings (EXA-164)
            if (event.key !== 'Enter' || event.shiftKey || event.altKey || event.isComposing) return false
            const sel = selectedTopBlock(view.state)
            if (!sel) return false
            view.dispatch(caretAfter(view.state, sel))
            return true
          },
          handlePaste(view, _event, slice) {
            const sel = selectedTopBlock(view.state)
            if (!sel) return false
            const tr = caretAfter(view.state, sel)
            view.dispatch(tr.replaceSelection(slice).scrollIntoView())
            return true
          },
        },
      }),
    ]
  },
})
