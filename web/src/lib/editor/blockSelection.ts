// A whole block selected (one click on a cover, a section, a question or an image) must never be
// replaced by what comes next (EXA-129): the toolbar's Section / Blank page / Page break went
// over it, and so did the first keystroke or a paste, so one click on the cover and a typed
// letter wiped the cover. Toolbar inserts go after the selected block's top-level block;
// Enter or a paste with a top-level block selected start after it. Backspace / Delete still
// delete a selected block on purpose.
//
// What a typed character does (EXA-171), whichever way it arrives (a key, a mobile keyboard's
// beforeinput, ProseMirror's own text input):
// - on a selected question (a generated or free-form question, or a part of one) nothing: there
//   single keys are commands (R, L, [, ]; shortcuts.ts), so the other letters do nothing too,
//   rather than half a word turning into text with the question locked on the way;
// - on any other selected top-level block (cover, section, blank page, image, page break) it
//   starts a paragraph after the block, as Enter does;
// - on any other block selected inside a question (an image in its body) nothing, and a paste
//   there is dropped too, so a question is never split.
// An input method (IME composition, a dead key) cannot be cancelled, so it moves the caret into
// a paragraph after the top-level block before it starts. Text selections are never touched.

import { Extension, type Editor, type JSONContent } from '@tiptap/core'
import {
  NodeSelection,
  Plugin,
  PluginKey,
  TextSelection,
  type EditorState,
  type Transaction,
} from '@tiptap/pm/state'
import type { EditorView } from '@tiptap/pm/view'
import { isMac } from '../keys'

/** The selected block, at any depth (a question, or a part or figure inside one). */
function selectedBlock(state: EditorState): NodeSelection | null {
  const sel = state.selection
  return sel instanceof NodeSelection && sel.node.isBlock ? sel : null
}

/** Where a block goes when the toolbar inserts one with a block selected: after the selected
 *  top-level block (a nested selection counts as its question), else null (insert at the caret). */
function afterSelectedBlock(state: EditorState): number | null {
  const sel = selectedBlock(state)
  if (!sel) return null
  return sel.$from.depth === 0 ? sel.to : sel.$from.after(1)
}

/** A transaction that adds an empty paragraph at `after` (the end of a top-level block) and
 *  puts the caret in it (or in the empty paragraph already there). */
function caretAt(state: EditorState, after: number): Transaction {
  const tr = state.tr
  const next = state.doc.resolve(after).nodeAfter
  if (!next || next.type.name !== 'paragraph' || next.content.size > 0) {
    tr.insert(after, state.schema.nodes.paragraph.create())
  }
  return tr.setSelection(TextSelection.create(tr.doc, after + 1))
}

/** The same, right after the selected top-level block. */
function caretAfter(state: EditorState, sel: NodeSelection): Transaction {
  return caretAt(state, sel.to)
}

/** Blocks on which a typed character does nothing: a question's single keys are its shortcuts. */
const QUESTION_TYPES = ['templatedQuestion', 'freeformQuestion', 'freeformPart']

/** Text typed with a block selected: dropped on a question or inside one, else it starts a
 *  paragraph after the block. */
function typeOver(view: EditorView, sel: NodeSelection, text: string): void {
  if (sel.$from.depth > 0 || QUESTION_TYPES.includes(sel.node.type.name)) return
  view.dispatch(caretAfter(view.state, sel).insertText(text).scrollIntoView())
}

/** An input method is about to compose with a block selected. Composition cannot be cancelled,
 *  so move the caret into a paragraph after the top-level block first. */
function leaveBlock(view: EditorView): void {
  const at = afterSelectedBlock(view.state)
  if (at !== null) view.dispatch(caretAt(view.state, at).scrollIntoView())
}

/** The character a key press types, or null for a command key or a chord. */
function typedChar(e: KeyboardEvent, mac = isMac()): string | null {
  // AltGr types characters and reports as Ctrl+Alt on Windows
  const altGraph = !!e.getModifierState?.('AltGraph')
  if (e.metaKey || (e.ctrlKey && !altGraph)) return null
  // Alt+letter types nothing on Windows and Linux; on a Mac ⌥ types (⌥8 is "•")
  if (e.altKey && !mac && !altGraph) return null
  return [...e.key].length === 1 ? e.key : null
}

/** A key that starts or continues an input method's composition, or a dead key's accent. */
function composes(e: KeyboardEvent): boolean {
  return e.isComposing || e.key === 'Process' || e.key === 'Dead'
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
            const sel = selectedBlock(view.state)
            if (!sel) return false
            typeOver(view, sel, text)
            return true
          },
          handleKeyDown(view, event) {
            const sel = selectedBlock(view.state)
            if (!sel) return false
            if (composes(event)) {
              if (event.target === view.dom) leaveBlock(view)
              return false // the input method goes on, in the new paragraph
            }
            if (event.key === 'Enter') {
              // Alt+Enter on a selected section or cover opens its settings (EXA-164)
              if (event.shiftKey || event.altKey || sel.$from.depth > 0) return false
              view.dispatch(caretAfter(view.state, sel))
              return true
            }
            // Keys from a control inside a block are that control's. The block shortcuts
            // (R, L, [, ]) ran before this, so a key that gets here types. Handled here rather
            // than on keypress, so no input rule sees it first.
            if (event.target !== view.dom) return false
            const text = typedChar(event)
            if (text === null) return false
            typeOver(view, sel, text)
            return true
          },
          handlePaste(view, _event, slice) {
            const sel = selectedBlock(view.state)
            if (!sel) return false
            if (sel.$from.depth > 0) return true // inside a question: never split it
            const tr = caretAfter(view.state, sel)
            view.dispatch(tr.replaceSelection(slice).scrollIntoView())
            return true
          },
          handleDOMEvents: {
            compositionstart(view) {
              if (selectedBlock(view.state)) leaveBlock(view)
              return false
            },
            // Mobile keyboards, dictation and the like insert without a key press.
            beforeinput(view, event) {
              const sel = selectedBlock(view.state)
              if (!sel || event.target !== view.dom || !event.inputType.startsWith('insert')) return false
              // a drop lands where it is dropped, never over the selection
              if (event.inputType === 'insertFromDrop') return false
              if (event.inputType === 'insertCompositionText') {
                leaveBlock(view) // cannot be cancelled
                return false
              }
              event.preventDefault()
              if (event.inputType === 'insertText' || event.inputType === 'insertReplacementText') {
                const text = event.data ?? event.dataTransfer?.getData('text/plain') ?? ''
                if (text) typeOver(view, sel, text)
              } else if (event.inputType === 'insertParagraph' || event.inputType === 'insertLineBreak') {
                if (sel.$from.depth === 0) view.dispatch(caretAfter(view.state, sel))
              }
              // anything else (a paste or drop the editor left alone, a yank) is dropped
              return true
            },
          },
        },
      }),
    ]
  },
})
