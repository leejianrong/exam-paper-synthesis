// The `templatedQuestion` TipTap node (ADR-0021): an atom holding a frozen canonical
// snapshot. Its node view mounts a Svelte component into the node's DOM — the one
// integration the plan flagged as a spike (Svelte 5 inside a ProseMirror node view).

import { Node } from '@tiptap/core'
import { NodeSelection, TextSelection } from '@tiptap/pm/state'
import { closeHistory } from '@tiptap/pm/history'
import type { Node as PMNode } from '@tiptap/pm/model'
import type { NodeViewRendererProps } from '@tiptap/core'
import { mount, unmount } from 'svelte'
import { writable } from 'svelte/store'
import { convertToFreeform } from '../api'
import type { Question } from '../types'
import QuestionBlock from './QuestionBlock.svelte'
import { freeformNode, newBlockId } from './doc'
import type { SwapMode } from './docsApi'
import { isGeneratedPosition } from './paperOps'
import { layoutOf, type BlockLayout } from './layout'
import { trackPlacement } from './sections'
import type { SectionPlacement } from './doc'
import { NOWHERE, trackPlace, type BlockPlace } from './blockPlace'

export interface TemplatedQuestionOptions {
  /** Open the "add question" picker to insert after the block at `pos`. */
  onAddBelow: (afterPos: number) => void
  /** A message for the page (e.g. which figure a conversion had to drop). */
  onNotice: (message: string) => void
  /** P8d: ask the server for another question in this block's place (the page saves first). */
  onSwap: (blockId: string, mode: SwapMode) => Promise<void>
  /** A question was deleted from its menu or with Del (EXA-161: the page offers Undo). */
  onDeleted: () => void
}

export const TemplatedQuestion = Node.create<TemplatedQuestionOptions>({
  name: 'templatedQuestion',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: false,

  addOptions() {
    return { onAddBelow: () => {}, onNotice: () => {}, onSwap: async () => {}, onDeleted: () => {} }
  },

  addAttributes() {
    return {
      block_id: { default: null },
      question: { default: null },
      remark: { default: null }, // the author's private note (inspector); never printed
      space_mm: { default: null }, // blank working space (mm); null = the default for its marks
      in_key: { default: true }, // false leaves it out of the answer key (P5)
      ans_unit: { default: null }, // unit printed after Ans:; null = the answer's own
      slot: { default: null }, // what the paper generator asked for here (P8a); kept, not shown
      locked: { default: false }, // P8d: kept as it is by "Regenerate unlocked"
    }
  },

  parseHTML() {
    return [{ tag: 'div[data-templated-question]' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', { 'data-templated-question': '', ...HTMLAttributes }]
  },

  addNodeView() {
    const options = this.options
    return ({ node, getPos, editor }: NodeViewRendererProps) => {
      const dom = document.createElement('div')
      dom.className = 'qblock'
      dom.setAttribute('data-block-id', String(node.attrs.block_id))
      // A question is one focusable group (EXA-161): focusing it shows its controls.
      dom.tabIndex = 0
      dom.setAttribute('role', 'group')
      dom.setAttribute('contenteditable', 'false') // an atom: keys on it are the block's, not typing

      const store = writable<Question>(node.attrs.question as Question)
      const layout = writable<BlockLayout>(layoutOf(node.attrs))
      const paperSlot = writable<PaperSlot>(slotOf(node.attrs))
      const placement = writable<SectionPlacement>('answer')
      const tracker = trackPlacement(editor, getPos, (p) => placement.set(p))
      const place = writable<BlockPlace>(NOWHERE)
      const stopPlace = trackPlace(editor, getPos, (p) => place.set(p))
      let current = node // the live node: attrs the inspector sets (remark) must survive edits here
      let latest = node.attrs.question as Question
      const store_value = () => latest
      /** Run `fn` on the block where it is now; if it has gone, drop the change (and say so). */
      const withBlock = (fn: (at: { pos: number; node: PMNode }) => void, late = false) => {
        const at = locateBlock(editor, getPos, current)
        if (at) return fn(at)
        if (late) options.onNotice('That question was removed before the change arrived.')
      }
      const setAttrs = (patch: Record<string, unknown>, late = false) =>
        withBlock(({ pos, node: live }) => {
          editor.view.dispatch(editor.state.tr.setNodeMarkup(pos, undefined, { ...live.attrs, ...patch }))
        }, late)

      const component = mount(QuestionBlock, {
        target: dom,
        props: {
          store: { subscribe: store.subscribe },
          layout: { subscribe: layout.subscribe },
          paperSlot: { subscribe: paperSlot.subscribe },
          placement: { subscribe: placement.subscribe },
          place: { subscribe: place.subscribe },
          host: dom,
          ctx: {
            // An edit's reply: it may arrive after the block was moved or deleted.
            replace: (q: Question) => setAttrs({ question: q }, true),
            setLayout: (patch: Partial<BlockLayout>) => setAttrs(patch),
            remove: () =>
              withBlock(({ pos, node: live }) => {
                editor
                  .chain()
                  .focus()
                  // its own undo step: the toast's Undo brings back just this question
                  .command(({ tr }) => {
                    closeHistory(tr)
                    return true
                  })
                  .deleteRange({ from: pos, to: pos + live.nodeSize })
                  .run()
                options.onDeleted()
              }),
            swap: (mode: SwapMode) => options.onSwap(String(current.attrs.block_id), mode),
            setLocked: (locked: boolean) => setAttrs({ locked }),
            setInKey: (in_key: boolean) => setAttrs({ in_key }),
            move: (dir: -1 | 1) =>
              withBlock(({ pos, node: live }) => {
                moveBlock(editor, pos, live.nodeSize, dir)
                refocus(dom)
              }),
            addBelow: () => withBlock(({ pos, node: live }) => options.onAddBelow(pos + live.nodeSize)),
            // Tier 3 (ADR-0021): the block becomes teacher-owned text, one undo step.
            convert: async () => {
              const out = await convertToFreeform(store_value())
              withBlock(({ pos, node: live }) => {
                const block = freeformNode()
                const json = {
                  ...block,
                  attrs: {
                    ...block.attrs,
                    marks: out.marks,
                    answer: out.answer,
                    remark: live.attrs.remark ?? null,
                  },
                  content: out.content,
                }
                const { tr, schema } = editor.state
                tr.replaceWith(pos, pos + live.nodeSize, schema.nodeFromJSON(json))
                editor.view.dispatch(tr)
                if (out.dropped.length) {
                  options.onNotice(`Now your own text. Not included: ${out.dropped.join('; ')}.`)
                }
              }, true)
            },
          },
        },
      })

      return {
        dom,
        update(updated) {
          if (updated.type !== node.type) return false
          current = updated
          latest = updated.attrs.question as Question
          store.set(latest)
          layout.set(layoutOf(updated.attrs))
          paperSlot.set(slotOf(updated.attrs))
          tracker.refresh()
          return true
        },
        // The Svelte component owns all interaction inside the block.
        stopEvent: () => true,
        ignoreMutation: () => true,
        destroy() {
          tracker.destroy()
          stopPlace()
          void unmount(component)
        },
      }
    }
  },
})

/** Where a question block is now, and its live node; null once it has gone. Anything that runs
 *  after a wait (an edit's reply) or from a node view that may be torn down acts only on the
 *  same block (same type and block_id), never on whatever now sits at its old position
 *  (EXA-161 review: a late reply used to land on position 0, the cover page). */
export function locateBlock(
  editor: NodeViewRendererProps['editor'],
  getPos: () => number | undefined,
  current: PMNode,
): { pos: number; node: PMNode } | null {
  if (editor.isDestroyed) return null
  const { doc } = editor.state
  const id = current.attrs.block_id
  const isMe = (n: PMNode | null | undefined): n is PMNode =>
    !!n && n.type === current.type && (id === null ? n === current : n.attrs.block_id === id)
  const p = getPos()
  if (typeof p === 'number' && p >= 0 && p < doc.content.size) {
    const n = doc.nodeAt(p)
    if (isMe(n)) return { pos: p, node: n }
  }
  if (id === null) return null
  // Moved (a move redraws the block): find it by its id.
  let found: { pos: number; node: PMNode } | null = null
  doc.forEach((child, offset) => {
    if (!found && isMe(child)) found = { pos: offset, node: child }
  })
  return found
}

/** P8d: whether the generator filled this block (it can be swapped) and whether it's locked. */
export interface PaperSlot {
  generated: boolean
  locked: boolean
  /** In the answer key (P5's in_key). */
  inKey: boolean
}

export function slotOf(attrs: Record<string, unknown>): PaperSlot {
  // Any generated question, slot or not: "Regenerate unlocked" refills it, so it can be
  // locked (and swapped) too. A bank question is never touched, so it gets neither.
  return {
    generated: isGeneratedPosition({ type: 'templatedQuestion', attrs }),
    locked: attrs.locked === true,
    inKey: attrs.in_key !== false,
  }
}

/** After a move ProseMirror redraws the block: keep keyboard focus on it (Alt+↑ again moves on). */
export function refocus(dom: HTMLElement) {
  const blockId = dom.getAttribute('data-block-id')
  queueMicrotask(() => {
    const target = dom.isConnected
      ? dom
      : document.querySelector<HTMLElement>(`[data-block-id="${blockId}"]`)
    if (target && target.tabIndex >= 0) target.focus()
  })
}

/** Swap a block with its previous/next sibling. A selection on or in the block moves with it,
 *  so Alt+↑ pressed again keeps moving the same question (EXA-161). */
export function moveBlock(
  editor: NodeViewRendererProps['editor'],
  pos: number,
  size: number,
  dir: -1 | 1,
) {
  const { doc, tr, selection } = editor.state
  const $pos = doc.resolve(pos)
  const index = $pos.index()
  const parent = $pos.parent
  const target = index + dir
  if (target < 0 || target >= parent.childCount) return
  const node = parent.child(index)
  const sibling = parent.child(target)
  let to: number
  if (dir === -1) {
    to = pos - sibling.nodeSize
    tr.delete(pos, pos + size).insert(to, node)
  } else {
    to = pos + sibling.nodeSize
    tr.insert(pos + size + sibling.nodeSize, node).delete(pos, pos + size)
  }
  if (selection.from >= pos && selection.to <= pos + size) {
    const shift = to - pos
    tr.setSelection(
      selection instanceof NodeSelection
        ? NodeSelection.create(tr.doc, selection.from + shift)
        : TextSelection.create(tr.doc, selection.anchor + shift, selection.head + shift),
    )
  }
  editor.view.dispatch(tr.scrollIntoView())
}

/** Build the node JSON for a freshly inserted question. */
export function questionNode(question: Question) {
  return {
    type: 'templatedQuestion',
    attrs: { block_id: newBlockId(), question },
  }
}
