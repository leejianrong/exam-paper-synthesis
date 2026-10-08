// The `freeformQuestion` TipTap node (W2a, ADR-0021): a question the teacher types straight
// onto the page. Unlike the templated atom its body is editable content (paragraphs and
// lists); `marks` and the written `answer` live in node attributes — the answer is edited
// in the answer-key region, not on the page. Chrome (marks field, move, delete) sits in a
// toolbar that never prints; `[n]` shows on the page exactly as it prints.

import { Node } from '@tiptap/core'
import type { NodeViewRendererProps } from '@tiptap/core'
import { EMPTY_ANSWER } from './doc'
import { moveBlock } from './templatedQuestion'

export interface FreeformQuestionOptions {
  onAddBelow: (afterPos: number) => void
}

const jsonAttr = <T>(name: string, fallback: T) => ({
  default: fallback,
  parseHTML: (el: HTMLElement): T => {
    try {
      const raw = el.getAttribute(name)
      return raw === null ? fallback : (JSON.parse(raw) as T)
    } catch {
      return fallback
    }
  },
  renderHTML: (attrs: Record<string, unknown>) => ({
    [name]: JSON.stringify(attrs[name.replace('data-', '')] ?? fallback),
  }),
})

function clampMarks(raw: string): number | null {
  if (raw.trim() === '') return null
  const n = Math.round(Number(raw))
  if (!Number.isFinite(n)) return null
  return Math.min(100, Math.max(0, n))
}

function el<K extends keyof HTMLElementTagNameMap>(tag: K, cls: string, text?: string) {
  const e = document.createElement(tag)
  e.className = cls
  if (text !== undefined) e.textContent = text
  return e
}

export const FreeformQuestion = Node.create<FreeformQuestionOptions>({
  name: 'freeformQuestion',
  // Its own group (not `block`) so a free-form question can only sit at the top level.
  group: 'question',
  content: '(paragraph | bulletList | orderedList | image)+',
  isolating: true,
  defining: true,
  draggable: false,

  addOptions() {
    return { onAddBelow: () => {} }
  },

  addAttributes() {
    return {
      block_id: { default: null },
      marks: jsonAttr<number | null>('data-marks', null),
      answer: jsonAttr('data-answer', EMPTY_ANSWER),
    }
  },

  parseHTML() {
    return [{ tag: 'div[data-freeform-question]' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', { 'data-freeform-question': '', ...HTMLAttributes }, 0]
  },

  addKeyboardShortcuts() {
    return {
      // Leave the block: a new paragraph after it, caret in it.
      'Mod-Enter': ({ editor }) => {
        const { $from } = editor.state.selection
        for (let d = $from.depth; d > 0; d--) {
          if ($from.node(d).type.name === this.name) {
            const after = $from.after(d)
            return editor
              .chain()
              .insertContentAt(after, { type: 'paragraph' })
              .setTextSelection(after + 1)
              .run()
          }
        }
        return false
      },
    }
  },

  addNodeView() {
    const options = this.options
    return ({ node, getPos, editor }: NodeViewRendererProps) => {
      let current = node
      const pos = () => {
        const p = getPos()
        return typeof p === 'number' ? p : 0
      }

      const dom = el('div', 'qblock ffblock')
      dom.setAttribute('data-block-id', String(node.attrs.block_id))
      const num = el('div', 'ff-num')
      num.contentEditable = 'false'
      num.setAttribute('aria-hidden', 'true')

      const main = el('div', 'ff-main')
      const row = el('div', 'ff-row')
      const contentDOM = el('div', 'ff-body')
      const marksEl = el('span', 'ff-marks')
      marksEl.contentEditable = 'false'
      row.append(contentDOM, marksEl)

      const bar = el('div', 'ff-bar')
      bar.contentEditable = 'false'
      bar.setAttribute('role', 'group')
      bar.setAttribute('aria-label', 'question tools')
      const label = el('label', 'ff-marks-field')
      label.append('Marks ')
      const input = el('input', 'ff-marks-input')
      input.type = 'number'
      input.min = '0'
      input.max = '100'
      input.setAttribute('aria-label', 'Marks')
      label.append(input)
      const button = (text: string, onClick: () => void, extra = '', aria?: string) => {
        const b = el('button', extra, text)
        b.type = 'button'
        if (aria) {
          b.setAttribute('aria-label', aria)
          b.title = aria
        }
        b.addEventListener('click', onClick)
        return b
      }
      const spacer = el('span', 'ff-spacer')
      bar.append(
        label,
        spacer,
        button('↑', () => moveBlock(editor, pos(), current.nodeSize, -1), '', 'Move up'),
        button('↓', () => moveBlock(editor, pos(), current.nodeSize, 1), '', 'Move down'),
        button('+ Add below', () => options.onAddBelow(pos() + current.nodeSize)),
        button(
          'Delete',
          () =>
            editor
              .chain()
              .focus()
              .deleteRange({ from: pos(), to: pos() + current.nodeSize })
              .run(),
          'danger',
        ),
      )

      input.addEventListener('change', () => {
        const marks = clampMarks(input.value)
        const { tr } = editor.state
        tr.setNodeMarkup(pos(), undefined, { ...current.attrs, marks })
        editor.view.dispatch(tr)
      })

      main.append(row, bar)
      dom.append(num, main)

      const sync = () => {
        const marks = current.attrs.marks as number | null
        marksEl.textContent = marks === null || marks === undefined ? '' : `[${marks}]`
        if (document.activeElement !== input) input.value = marks === null ? '' : String(marks)
      }
      sync()

      return {
        dom,
        contentDOM,
        update(updated) {
          if (updated.type !== node.type) return false
          current = updated
          dom.setAttribute('data-block-id', String(updated.attrs.block_id))
          sync()
          return true
        },
        // Clicks and typing in the toolbar are ours; the body is ProseMirror's.
        stopEvent: (event) => bar.contains(event.target as globalThis.Node),
        ignoreMutation: (m) => !contentDOM.contains(m.target),
      }
    }
  },
})

/** Insert a free-form block at `at` and put the caret in it. */
export function insertFreeform(editor: NodeViewRendererProps['editor'], at: number, node: object) {
  editor
    .chain()
    .insertContentAt(at, node)
    .setTextSelection(at + 2)
    .run()
  // Synchronous: the chain's `.focus()` defers a frame, and keystrokes typed in between
  // would land nowhere.
  editor.view.focus()
}

/** The document node, widened so free-form questions (group `question`) can sit in it. */
export const QuestionDocument = Node.create({
  name: 'doc',
  topNode: true,
  content: '(block | question | media)+',
})
