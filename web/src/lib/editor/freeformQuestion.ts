// The `freeformQuestion` TipTap node (W2a, ADR-0021): a question the teacher types straight
// onto the page. Unlike the templated atom its body is editable content (paragraphs and
// lists); `marks` and the written `answer` live in node attributes — the answer is edited
// in the answer-key region, not on the page. Chrome (marks field, move, delete) sits in a
// toolbar that never prints; `[n]` shows on the page exactly as it prints.

import { Node } from '@tiptap/core'
import { Plugin } from '@tiptap/pm/state'
import type { NodeViewRendererProps } from '@tiptap/core'
import { EMPTY_ANSWER } from './doc'
import { moveBlock } from './templatedQuestion'
import { FreeformPart, MAX_PARTS, PART_NODE, jsonAttr, partLetter } from './freeformPart'
import { mount, unmount } from 'svelte'
import { get, writable } from 'svelte/store'
import FreeformArea from './FreeformArea.svelte'
import { DEFAULT_PLACEMENT, layoutOf } from './layout'
import { paperSettings } from './paperSettings'

export interface FreeformQuestionOptions {
  onAddBelow: (afterPos: number) => void
}

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
  // The body, then optionally the lettered parts (P3).
  content: '(paragraph | bulletList | orderedList | image)+ freeformPart*',
  isolating: true,
  defining: true,
  draggable: false,

  // The lettered parts are part of this node's vocabulary: anything that registers a
  // free-form question gets them.
  addExtensions() {
    return [FreeformPart]
  },

  addOptions() {
    return { onAddBelow: () => {} }
  },

  addAttributes() {
    return {
      block_id: { default: null },
      marks: jsonAttr<number | null>('data-marks', null),
      answer: jsonAttr('data-answer', EMPTY_ANSWER),
      remark: { default: null }, // the author's private note (inspector); never printed
      space_mm: jsonAttr<number | null>('data-space_mm', null), // blank working space (mm)
      ans_unit: jsonAttr<string | null>('data-ans_unit', null), // unit printed after Ans:
    }
  },

  parseHTML() {
    return [{ tag: 'div[data-freeform-question]' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', { 'data-freeform-question': '', ...HTMLAttributes }, 0]
  },

  addProseMirrorPlugins() {
    // A pasted question with more than MAX_PARTS parts would save fine in the editor and be
    // refused by the server; refuse it here instead.
    return [
      new Plugin({
        filterTransaction: (tr) => {
          if (!tr.docChanged) return true
          let ok = true
          tr.doc.forEach((n) => {
            if (n.type.name !== this.name) return
            let parts = 0
            n.forEach((c) => {
              if (c.type.name === PART_NODE) parts++
            })
            if (parts > MAX_PARTS) ok = false
          })
          return ok
        },
      }),
    ]
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
      const totalEl = el('span', 'ff-total')
      const addPartBtn = button('+ Add part', () => addPart(), '', 'Add a lettered part')
      bar.append(
        label,
        totalEl,
        spacer,
        button('↑', () => moveBlock(editor, pos(), current.nodeSize, -1), '', 'Move up'),
        button('↓', () => moveBlock(editor, pos(), current.nodeSize, 1), '', 'Move down'),
        addPartBtn,
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

      const parts = () => {
        const out: Array<{ marks: number }> = []
        current.forEach((c) => {
          if (c.type.name === PART_NODE) out.push({ marks: (c.attrs.marks as number | null) ?? 0 })
        })
        return out
      }
      // Adding the first part moves the marks onto the parts: one undoable step.
      function addPart() {
        if (parts().length >= MAX_PARTS) return
        const { tr, schema } = editor.state
        const at = pos() + current.nodeSize - 1 // the end of the question's content
        // The first part takes over the question's marks and written answer (nothing is lost);
        // later parts start at one mark.
        const first = parts().length === 0
        const part = schema.nodes[PART_NODE].create(
          first
            ? { marks: current.attrs.marks ?? 1, answer: current.attrs.answer }
            : { marks: 1 },
          [schema.nodes.paragraph.create()],
        )
        tr.insert(at, part)
        if (first) {
          tr.setNodeMarkup(pos(), undefined, { ...current.attrs, marks: null, answer: EMPTY_ANSWER })
        }
        editor.view.dispatch(tr)
        editor.commands.focus(at + 2)
      }

      input.addEventListener('change', () => {
        const marks = clampMarks(input.value)
        const { tr } = editor.state
        tr.setNodeMarkup(pos(), undefined, { ...current.attrs, marks })
        editor.view.dispatch(tr)
      })

      const areaHost = el('div', 'ff-area')
      areaHost.contentEditable = 'false'
      main.append(row, areaHost, bar)
      dom.append(num, main)

      const setLayout = (patch: Record<string, unknown>) => {
        const { tr } = editor.state
        tr.setNodeMarkup(pos(), undefined, { ...current.attrs, ...patch })
        editor.view.dispatch(tr)
      }
      const areaState = writable(areaProps())
      const area = mount(FreeformArea, {
        target: areaHost,
        props: {
          state: { subscribe: areaState.subscribe },
          onSpace: (mm: number | null) => setLayout({ space_mm: mm }),
          onUnit: (u: string) => setLayout({ ans_unit: u }),
        },
      })
      function areaProps() {
        const l = layoutOf(current.attrs)
        return {
          marks: (current.attrs.marks as number | null) ?? null,
          spaceMm: l.space_mm,
          unit: l.ans_unit,
          placement: get(paperSettings).marks_placement ?? DEFAULT_PLACEMENT,
        }
      }

      const sync = () => {
        const ps = parts()
        const multi = ps.length > 0
        dom.classList.toggle('multipart', multi)
        // With parts the marks are the parts' sum and the question has no answer area of its own.
        label.hidden = multi
        areaHost.hidden = multi
        marksEl.hidden = multi
        totalEl.textContent = multi
          ? `${ps.length} part${ps.length === 1 ? '' : 's'} · ${ps.reduce((n, p) => n + p.marks, 0)} marks`
          : ''
        addPartBtn.disabled = ps.length >= MAX_PARTS
        // Parts are lettered by position: relabel after any change to the siblings.
        // (After ProseMirror has patched the parts' DOM, which happens once update() returns.)
        queueMicrotask(() =>
          dom.querySelectorAll('.ffp-label').forEach((n, i) => (n.textContent = `(${partLetter(i)})`)),
        )
        const marks = current.attrs.marks as number | null
        const placement = get(paperSettings).marks_placement ?? DEFAULT_PLACEMENT
        marksEl.textContent =
          marks === null || marks === undefined || placement === 'answer' ? '' : `[${marks}]`
        if (document.activeElement !== input) input.value = marks === null ? '' : String(marks)
      }
      sync()
      const unsubscribe = paperSettings.subscribe(() => {
        sync()
        areaState.set(areaProps())
      })

      return {
        dom,
        contentDOM,
        update(updated) {
          if (updated.type !== node.type) return false
          current = updated
          dom.setAttribute('data-block-id', String(updated.attrs.block_id))
          sync()
          areaState.set(areaProps())
          return true
        },
        destroy() {
          unsubscribe()
          void unmount(area)
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
