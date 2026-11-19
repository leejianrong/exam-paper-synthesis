// A whole block selected (one click on a cover, a section, a question or an image) must never be
// replaced by what comes next (EXA-129): the toolbar's Section / Blank page / Page break went
// over it, and so did the first keystroke or a paste, so one click on the cover and a typed
// letter wiped the cover. Toolbar inserts go after the selected block's top-level block;
// Enter, Shift+Enter or a paste with a top-level block selected start after it. Backspace /
// Delete still delete a selected block on purpose.
//
// What a typed character does (EXA-171), whichever way it arrives (a key, a keyboard's
// beforeinput, ProseMirror's own text input):
// - on a selected question (a generated or free-form question, or a part of one) nothing: there
//   single keys are commands (R, L, [, ]; shortcuts.ts), so the other letters do nothing too,
//   rather than half a word turning into text with the question locked on the way. The
//   question's pill says once "Press Enter to write below" (TYPED_ON_QUESTION);
// - on any other selected top-level block (cover, section, blank page, image, page break) it
//   starts a paragraph after the block, as Enter does;
// - on any block selected below the top level (a part, an image in a question's body) nothing,
//   and Shift+Enter or a pasted text there do nothing either (Enter is left to the editor), so
//   a question is never split. A pasted picture alone is left to the image upload, which puts
//   it next to the selection, never over it (media.ts).
// The exception is an input method's composition (IME, a mobile keyboard that composes words,
// such as Gboard): it cannot be cancelled, so once it starts it moves the caret into a paragraph
// after the top-level block and the composed text lands there. Text selections are never touched.

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
import { imageFiles } from './assets'

/** Fired (bubbling) on a selected question's DOM when a typed key was dropped on it, so its
 *  pill can say how to write below it. */
export const TYPED_ON_QUESTION = 'exam:typed-on-question'

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

/** Text typed with a block selected: dropped on a question or on any block below the top
 *  level, else it starts a paragraph after the block. */
function typeOver(view: EditorView, sel: NodeSelection, text: string): void {
  if (sel.$from.depth > 0) return
  if (QUESTION_TYPES.includes(sel.node.type.name)) {
    view.nodeDOM(sel.from)?.dispatchEvent(new CustomEvent(TYPED_ON_QUESTION, { bubbles: true }))
    return
  }
  view.dispatch(caretAfter(view.state, sel).insertText(text).scrollIntoView())
}

/** An input method is composing (or about to) with a block selected. Composition cannot be
 *  cancelled, so move the caret into a paragraph after the top-level block. */
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

/** A key pressed while an input method composes, or opening one ('Process'). A dead key is not
 *  one: it may compose nothing, so for it the caret moves only once composition starts. */
function composes(e: KeyboardEvent): boolean {
  return e.isComposing || e.key === 'Process'
}

/** ProseMirror on iOS lets Enter through and replays it as a synthetic Enter key ~200 ms later
 *  (its `lastIOSEnter`); true while such a replay is pending. */
function iosEnterPending(view: EditorView): boolean {
  const last = (view as unknown as { input?: { lastIOSEnter?: number } }).input?.lastIOSEnter ?? 0
  return last > Date.now() - 225
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
  // Ahead of StarterKit's keys and input rules wherever it is listed (Shift+Enter's hard break
  // replaces a selected block), behind the block shortcuts (1000), which take R, L, [ and ] first.
  priority: 500,
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
              if (event.altKey) return false
              // Ctrl/Cmd+Enter adds a question (the page's own key handler, which ran first);
              // here it must not reach the hard break's Mod-Enter, which would replace the
              // block. Inside a question it stays the question's own.
              if (event.ctrlKey || event.metaKey) return sel.$from.depth === 0
              if (sel.$from.depth > 0) return event.shiftKey // a part: Shift+Enter does nothing
              view.dispatch(caretAfter(view.state, sel))
              return true
            }
            // Keys from a control inside a block (a select in a question) are that control's.
            // The block shortcuts ran before this, so a key that gets here types. Handled here
            // rather than on keypress, so no input rule sees it first.
            if (event.target !== view.dom) return false
            const text = typedChar(event)
            if (text === null) return false
            typeOver(view, sel, text)
            return true
          },
          handlePaste(view, event, slice) {
            const sel = selectedBlock(view.state)
            if (!sel) return false
            // A pasted picture alone is the image upload's: it inserts a figure next to the
            // selection (media.ts insertBlock), never over it.
            if (imageFiles(event.clipboardData).length && !event.clipboardData?.getData('text/plain')) return false
            if (sel.$from.depth > 0) return true // below the top level: dropped
            const tr = caretAfter(view.state, sel)
            view.dispatch(tr.replaceSelection(slice).scrollIntoView())
            return true
          },
          handleDOMEvents: {
            compositionstart(view, event) {
              if (event.target !== view.dom) return false
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
                // On iOS ProseMirror replays this Enter as a key shortly, which reaches the
                // Enter branch above with the block still selected; acting now too would add a
                // second paragraph.
                if (sel.$from.depth === 0 && !iosEnterPending(view)) view.dispatch(caretAfter(view.state, sel))
              }
              // anything else (a paste the editor left alone, a yank) is dropped
              return true
            },
          },
        },
      }),
    ]
  },
})
