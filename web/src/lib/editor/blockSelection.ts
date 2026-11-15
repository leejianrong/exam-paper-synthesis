// A whole block selected (one click on a cover, a section, a question or an image) must never be
// replaced by what comes next (EXA-129): the toolbar's Section / Blank page / Page break went
// over it, and so did the first keystroke, so one click on the cover and a typed letter wiped
// the cover. Toolbar inserts go after a selected block; typing or Enter with a block selected
// starts a new paragraph after it. Backspace / Delete still delete a selected block on purpose.

import { Extension, type Editor, type JSONContent } from '@tiptap/core'
import { NodeSelection, Plugin, PluginKey, TextSelection, type EditorState, type Transaction } from '@tiptap/pm/state'

function selectedBlock(state: EditorState): NodeSelection | null {
  const sel = state.selection
  return sel instanceof NodeSelection && sel.node.isBlock ? sel : null
}

/** A transaction that adds an empty paragraph right after the selected block and puts the
 *  caret in it (or in the paragraph already there). */
function caretAfter(state: EditorState, sel: NodeSelection): Transaction {
  const tr = state.tr
  const after = sel.to
  const next = state.doc.resolve(after).nodeAfter
  if (!next || next.type.name !== 'paragraph' || next.content.size > 0) {
    tr.insert(after, state.schema.nodes.paragraph.create())
  }
  return tr.setSelection(TextSelection.create(tr.doc, after + 1))
}

/** Insert a block: after a selected block (never over it), else as `insertContent` would. */
export function insertBlockSafely(editor: Editor, content: JSONContent): void {
  const sel = selectedBlock(editor.state)
  if (sel) {
    editor.chain().insertContentAt(sel.to, content).run()
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
            const sel = selectedBlock(view.state)
            if (!sel) return false
            const tr = caretAfter(view.state, sel)
            view.dispatch(tr.insertText(text))
            return true
          },
          handleKeyDown(view, event) {
            if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return false
            const sel = selectedBlock(view.state)
            if (!sel) return false
            view.dispatch(caretAfter(view.state, sel))
            return true
          },
        },
      }),
    ]
  },
})
