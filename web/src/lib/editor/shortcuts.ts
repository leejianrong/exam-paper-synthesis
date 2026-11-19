import { Extension } from '@tiptap/core'
import { NodeSelection, Plugin, PluginKey } from '@tiptap/pm/state'
import { isMac } from '../keys'

export { ariaKeys, isMac, keyLabel } from '../keys'

// Keyboard shortcuts (EXA-161 block keys, EXA-163 global keys). A shortcut is named by the
// label it shows right-aligned in a menu ("R", "Alt+↑", "Ctrl+K"), so a key does exactly what
// the visible menu row with that label does, and a row that is hidden has no shortcut. Labels
// are written the PC way; `keyLabel` shows them the Mac way (⌘, ⌥) on a Mac, where Cmd stands
// in for Ctrl.

/** The editor-wide shortcuts (UI-REDESIGN 6). Each one is a chord with Ctrl (Cmd on a Mac), so
 *  none of them types a character; typing keys (Ctrl+B/I/U, Ctrl+Z/Y) stay the editor's and the
 *  browser keeps its own (Ctrl+R, L, T, W). */
export const GLOBAL_KEYS = {
  palette: 'Ctrl+K',
  addQuestion: 'Ctrl+Enter',
  answerKey: 'Ctrl+Alt+K',
  preview: 'Ctrl+P',
  panel: 'Ctrl+\\',
  sheet: 'Ctrl+/',
  equation: 'Ctrl+M',
} as const

export type GlobalCommand = keyof typeof GLOBAL_KEYS

/** Commands that put something into the paper: they never fire from a form field (the title,
 *  a marks box, a dialog's input), only from the page itself. */
const INSERTS: GlobalCommand[] = ['addQuestion', 'equation']

/** Which editor-wide command a key press asks for, or null. `fromField` is true when the key
 *  was pressed in an input, text area or select. */
export function globalShortcut(e: KeyboardEvent, fromField = false, mac = isMac()): GlobalCommand | null {
  if (e.isComposing) return null
  // AltGr reports as Ctrl+Alt on Windows: AltGr+K types "ł" on some layouts, never a shortcut
  if (e.getModifierState?.('AltGraph')) return null
  const mod = mac ? e.metaKey && !e.ctrlKey : e.ctrlKey && !e.metaKey
  if (!mod) return null
  // Read e.key, the character the layout gives, so a chord follows the key's printed label
  // (Ctrl+- on a German keyboard is zoom out, wherever "/" sits on a US one). Only on a Mac,
  // where ⌥ changes e.key (⌥K is "˚"), is an ⌥ chord read by its physical key.
  const key = e.key.length === 1 ? e.key.toLowerCase() : e.key
  let cmd: GlobalCommand | null = null
  if (e.altKey) {
    if (!e.shiftKey && (key === 'k' || (mac && e.code === 'KeyK'))) cmd = 'answerKey'
  } else if (key === '/') {
    // "/" is Shift+7 on many layouts, so Shift may come with it
    cmd = 'sheet'
  } else if (!e.shiftKey) {
    if (key === 'k') cmd = 'palette'
    else if (key === 'Enter') cmd = 'addQuestion'
    else if (key === 'p') cmd = 'preview'
    else if (key === '\\') cmd = 'panel'
    else if (key === 'm') cmd = 'equation'
  }
  if (cmd && fromField && INSERTS.includes(cmd)) return null
  return cmd
}

/** The shortcut sheet (Ctrl+/): every shortcut, grouped as a teacher thinks of them. */
export const SHEET: Array<{ group: string; rows: Array<{ label: string; keys: string[] }> }> = [
  {
    group: 'Paper',
    rows: [
      { label: 'Find a command', keys: [GLOBAL_KEYS.palette] },
      { label: 'Add a question', keys: [GLOBAL_KEYS.addQuestion] },
      { label: 'Switch to the answer key and back', keys: [GLOBAL_KEYS.answerKey] },
      { label: 'Preview pages', keys: [GLOBAL_KEYS.preview] },
      { label: 'Show or hide the side panel', keys: [GLOBAL_KEYS.panel] },
      { label: 'Keyboard shortcuts', keys: [GLOBAL_KEYS.sheet] },
    ],
  },
  {
    group: 'Questions',
    rows: [
      { label: 'Another like this', keys: ['R'] },
      { label: 'Lock or unlock', keys: ['L'] },
      { label: 'Make easier', keys: ['['] },
      { label: 'Make harder', keys: [']'] },
      { label: 'Move up', keys: ['Alt+↑'] },
      { label: 'Move down', keys: ['Alt+↓'] },
      { label: 'Delete', keys: ['Del'] },
      { label: "Open the question's menu", keys: ['Shift+F10'] },
    ],
  },
  {
    group: 'Text',
    rows: [
      { label: 'Bold', keys: ['Ctrl+B'] },
      { label: 'Italic', keys: ['Ctrl+I'] },
      { label: 'Underline', keys: ['Ctrl+U'] },
      { label: 'Equation', keys: [GLOBAL_KEYS.equation] },
      { label: 'Line break', keys: ['Shift+Enter'] },
      { label: 'Undo', keys: ['Ctrl+Z'] },
      { label: 'Redo', keys: ['Ctrl+Y'] },
    ],
  },
]

/** A command the palette (Ctrl+K) can run: a menu row or a question action, by name. */
export interface Command {
  label: string
  /** Where it lives: "Paper", "Insert", "Question 6", … */
  group: string
  shortcut?: string
  run: () => void
}

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

/** May a key on `target` act as a block shortcut of the block `host`? Only on the block itself,
 *  its ⋮⋮ handle or a pill button (EXA-161 review); never on any other control inside it
 *  (the working-space grip, a part's "Delete part", the names form, a select, a link, the
 *  open menu, or anything marked `data-own-keys`). */
export function isBlockKeyTarget(target: EventTarget | null, host: Element): boolean {
  if (!(target instanceof HTMLElement)) return false
  if (target === host) return true
  if (!host.contains(target) || target.closest('[data-own-keys], [role="menu"]')) return false
  return target.matches('.qhandle') || (target.tagName === 'BUTTON' && !!target.closest('.qpill'))
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

/** The question menus' rows by block, for the command palette: a block lists its rows while it
 *  is mounted. */
const blockCommands = new WeakMap<Element, () => Command[]>()

export function registerBlockCommands(dom: Element, list: () => Command[]): () => void {
  blockCommands.set(dom, list)
  return () => {
    if (blockCommands.get(dom) === list) blockCommands.delete(dom)
  }
}

export function commandsForBlock(dom: Element | null | undefined): Command[] {
  return dom ? (blockCommands.get(dom)?.() ?? []) : []
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
            // Keys from a control inside a block (a part's button, a grip) are that control's.
            if (event.target !== view.dom) return false
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
