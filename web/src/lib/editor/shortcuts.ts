import { Extension } from '@tiptap/core'
import { NodeSelection, Plugin, PluginKey } from '@tiptap/pm/state'

// Keyboard shortcuts (EXA-161; S5/EXA-163 adds the global ones here). A shortcut is named by
// the label it shows right-aligned in a menu ("R", "Alt+↑"), so a key does exactly what the
// visible menu row with that label does, and a row that is hidden has no shortcut.

/** The block shortcuts: active on a focused or selected question, never while typing. */
export const BLOCK_KEYS = {
  like: 'R',
  lock: 'L',
  easier: '[',
  harder: ']',
  up: 'Alt+↑',
  down: 'Alt+↓',
  delete: 'Del',
} as const

export type BlockKey = (typeof BLOCK_KEYS)[keyof typeof BLOCK_KEYS]

/** What a key press on a question block asks for: a shortcut's label, "menu" (Shift+F10 or the
 *  ContextMenu key), or null. `inText` is true while the caret is in text the author types in
 *  (a free-form question's body): then only chords that never type a character count. */
export function blockShortcut(e: KeyboardEvent, inText: boolean): BlockKey | 'menu' | null {
  if (e.isComposing || e.ctrlKey || e.metaKey) return null
  if (e.key === 'ContextMenu' || (e.key === 'F10' && e.shiftKey)) return 'menu'
  if (e.altKey) {
    if (e.shiftKey) return null
    if (e.key === 'ArrowUp') return BLOCK_KEYS.up
    if (e.key === 'ArrowDown') return BLOCK_KEYS.down
    return null
  }
  if (inText || e.shiftKey) return null
  switch (e.key) {
    case 'r':
    case 'R':
      return BLOCK_KEYS.like
    case 'l':
    case 'L':
      return BLOCK_KEYS.lock
    case '[':
      return BLOCK_KEYS.easier
    case ']':
      return BLOCK_KEYS.harder
    case 'Delete':
    case 'Backspace':
      return BLOCK_KEYS.delete
    default:
      return null
  }
}

/** Is the event's target somewhere the author types (an input, a text area, editable text)? */
export function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  if (target.matches('input, textarea, select')) return true
  // The nearest contenteditable decides (jsdom has no isContentEditable).
  const host = target.closest('[contenteditable]')
  return !!host && host.getAttribute('contenteditable') !== 'false'
}

/** The question blocks' key handlers, by their node view's DOM: the editor plugin looks up the
 *  selected block's handler when the editor itself has focus (a block selected with the arrow
 *  keys, or the caret in a free-form question). */
export type BlockKeyHandler = (e: KeyboardEvent, inText: boolean) => boolean
const handlers = new WeakMap<Element, BlockKeyHandler>()

export function registerBlockKeys(dom: Element, handler: BlockKeyHandler): () => void {
  handlers.set(dom, handler)
  return () => {
    if (handlers.get(dom) === handler) handlers.delete(dom)
  }
}

export function blockKeyHandler(dom: Element | null | undefined): BlockKeyHandler | undefined {
  return dom ? handlers.get(dom) : undefined
}

/** The editor's side of the block shortcuts: with a question selected as a block (arrow keys,
 *  or after a swap) or the caret in a free-form question, a key goes to that block's handler.
 *  Runs ahead of the editor's own keys, so Del on a selected question offers Undo. */
export const BlockShortcuts = Extension.create({
  name: 'blockShortcuts',
  priority: 1000,
  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey('blockShortcuts'),
        props: {
          handleKeyDown(view, event) {
            const sel = view.state.selection
            if (sel instanceof NodeSelection && sel.$from.depth === 0) {
              if (!QUESTION_NODES.includes(sel.node.type.name)) return false
              return blockKeyHandler(view.nodeDOM(sel.from) as Element | null)?.(event, false) ?? false
            }
            const { $from, $to } = sel
            if ($from.depth < 1 || $from.node(1).type.name !== 'freeformQuestion') return false
            if ($to.depth < 1 || $to.before(1) !== $from.before(1)) return false
            return blockKeyHandler(view.nodeDOM($from.before(1)) as Element | null)?.(event, true) ?? false
          },
        },
      }),
    ]
  },
})

const QUESTION_NODES = ['templatedQuestion', 'freeformQuestion']
