// The `freeformPart` TipTap node (P3): one lettered part — (a), (b)… — of a multi-part
// free-form question. It lives inside a `freeformQuestion`, after the question's body. Its
// label is its position (never stored), so deleting (a) relabels (b) as (a). Each part has
// its own marks, working space, Ans: line (unit) and written answer; the answer is edited in
// the answer-key region, like a single-part question's.

import { Node } from '@tiptap/core'
import type { NodeViewRendererProps } from '@tiptap/core'
import { mount, unmount } from 'svelte'
import { get, writable } from 'svelte/store'
import { EMPTY_ANSWER } from './doc'
import FreeformArea from './FreeformArea.svelte'
import { DEFAULT_PLACEMENT, layoutOf } from './layout'
import { paperSettings } from './paperSettings'

export const PART_NODE = 'freeformPart'
export const MAX_PARTS = 10

/** "a" for the first part, "b" for the second… */
export const partLetter = (index: number): string => String.fromCharCode(97 + index)

/** An attribute carried as JSON in an HTML attribute, so copy/paste round-trips objects and numbers. */
export const jsonAttr = <T>(name: string, fallback: T) => ({
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

/** Position of the part among its question's parts (0-based), from the live document. */
export function partIndex(editor: NodeViewRendererProps['editor'], pos: number): number {
  const $pos = editor.state.doc.resolve(pos)
  let n = 0
  for (let i = 0; i < $pos.index(); i++) if ($pos.parent.child(i).type.name === PART_NODE) n++
  return n
}

export const FreeformPart = Node.create({
  name: PART_NODE,
  group: 'questionpart',
  content: '(paragraph | bulletList | orderedList | image)+',
  isolating: true,
  defining: true,
  draggable: false,

  addAttributes() {
    return {
      marks: jsonAttr<number | null>('data-marks', 1),
      answer: jsonAttr('data-answer', EMPTY_ANSWER),
      space_mm: jsonAttr<number | null>('data-space_mm', null),
      ans_unit: jsonAttr<string | null>('data-ans_unit', null),
    }
  },

  parseHTML() {
    return [{ tag: 'div[data-freeform-part]' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', { 'data-freeform-part': '', ...HTMLAttributes }, 0]
  },

  addNodeView() {
    return ({ node, getPos, editor }: NodeViewRendererProps) => {
      let current = node
      const pos = () => {
        const p = getPos()
        return typeof p === 'number' ? p : 0
      }
      const letter = () => partLetter(partIndex(editor, pos()))

      const dom = el('div', 'ffpart')
      const head = el('div', 'ffp-head')
      const label = el('span', 'ffp-label', `(${letter()})`)
      label.contentEditable = 'false'
      const contentDOM = el('div', 'ffp-body')
      const marksEl = el('span', 'ffp-marks')
      marksEl.contentEditable = 'false'
      head.append(label, contentDOM, marksEl)

      const areaHost = el('div', 'ffp-area')
      areaHost.contentEditable = 'false'

      const bar = el('div', 'ffp-bar')
      bar.contentEditable = 'false'
      bar.setAttribute('role', 'group')
      bar.setAttribute('aria-label', 'part tools')
      const field = el('label', 'ffp-marks-field')
      field.append('Marks ')
      const input = el('input', 'ff-marks-input')
      input.type = 'number'
      input.min = '0'
      input.max = '100'
      input.setAttribute('aria-label', 'Part marks')
      field.append(input)
      const del = el('button', 'danger', 'Delete part')
      del.type = 'button'
      del.addEventListener('click', () => {
        const { tr, doc } = editor.state
        const $pos = doc.resolve(pos())
        const parent = $pos.parent
        let parts = 0
        parent.forEach((c) => {
          if (c.type.name === PART_NODE) parts++
        })
        tr.delete(pos(), pos() + current.nodeSize)
        // Deleting the only part makes the question single-part again: it takes the part's
        // marks and answer back, so nothing the teacher wrote is lost.
        if (parts === 1) {
          const qPos = $pos.before($pos.depth)
          tr.setNodeMarkup(qPos, undefined, {
            ...parent.attrs,
            marks: current.attrs.marks ?? null,
            answer: current.attrs.answer ?? EMPTY_ANSWER,
          })
        }
        editor.view.dispatch(tr)
        editor.view.focus()
      })
      bar.append(field, el('span', 'ff-spacer'), del)

      const patch = (attrs: Record<string, unknown>) => {
        const { tr } = editor.state
        tr.setNodeMarkup(pos(), undefined, { ...current.attrs, ...attrs })
        editor.view.dispatch(tr)
      }
      input.addEventListener('change', () => patch({ marks: clampMarks(input.value) }))

      const areaProps = () => {
        const l = layoutOf(current.attrs)
        return {
          marks: (current.attrs.marks as number | null) ?? null,
          spaceMm: l.space_mm,
          unit: l.ans_unit,
          placement: get(paperSettings).marks_placement ?? DEFAULT_PLACEMENT,
          label: letter(),
        }
      }
      const areaState = writable(areaProps())
      const area = mount(FreeformArea, {
        target: areaHost,
        props: {
          state: { subscribe: areaState.subscribe },
          onSpace: (mm: number | null) => patch({ space_mm: mm }),
          onUnit: (u: string) => patch({ ans_unit: u }),
        },
      })

      const sync = () => {
        const marks = (current.attrs.marks as number | null) ?? null
        const placement = get(paperSettings).marks_placement ?? DEFAULT_PLACEMENT
        marksEl.textContent = marks === null || placement === 'answer' ? '' : `[${marks}]`
        label.textContent = `(${letter()})`
        if (document.activeElement !== input) input.value = marks === null ? '' : String(marks)
        areaState.set(areaProps())
      }
      sync()
      const unsubscribe = paperSettings.subscribe(sync)
      dom.append(head, areaHost, bar)

      return {
        dom,
        contentDOM,
        update(updated) {
          if (updated.type !== node.type) return false
          current = updated
          sync()
          return true
        },
        destroy() {
          unsubscribe()
          void unmount(area)
        },
        stopEvent: (event) => bar.contains(event.target as globalThis.Node),
        ignoreMutation: (m) => !contentDOM.contains(m.target),
      }
    }
  },
})
