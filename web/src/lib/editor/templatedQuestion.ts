// The `templatedQuestion` TipTap node (ADR-0021): an atom holding a frozen canonical
// snapshot. Its node view mounts a Svelte component into the node's DOM — the one
// integration the plan flagged as a spike (Svelte 5 inside a ProseMirror node view).

import { Node } from '@tiptap/core'
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

export interface TemplatedQuestionOptions {
  /** Open the "add question" picker to insert after the block at `pos`. */
  onAddBelow: (afterPos: number) => void
  /** A message for the page (e.g. which figure a conversion had to drop). */
  onNotice: (message: string) => void
  /** P8d: ask the server for another question in this block's place (the page saves first). */
  onSwap: (blockId: string, mode: SwapMode) => Promise<void>
}

export const TemplatedQuestion = Node.create<TemplatedQuestionOptions>({
  name: 'templatedQuestion',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: false,

  addOptions() {
    return { onAddBelow: () => {}, onNotice: () => {}, onSwap: async () => {} }
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

      const store = writable<Question>(node.attrs.question as Question)
      const layout = writable<BlockLayout>(layoutOf(node.attrs))
      const paperSlot = writable<PaperSlot>(slotOf(node.attrs))
      let current = node // the live node: attrs the inspector sets (remark) must survive edits here
      let latest = node.attrs.question as Question
      const store_value = () => latest
      const pos = () => {
        const p = getPos()
        return typeof p === 'number' ? p : 0
      }

      const component = mount(QuestionBlock, {
        target: dom,
        props: {
          store: { subscribe: store.subscribe },
          layout: { subscribe: layout.subscribe },
          paperSlot: { subscribe: paperSlot.subscribe },
          ctx: {
            replace: (q: Question) => {
              const { tr } = editor.state
              tr.setNodeMarkup(pos(), undefined, {
                ...current.attrs,
                question: q,
              })
              editor.view.dispatch(tr)
            },
            setLayout: (patch: Partial<BlockLayout>) => {
              const { tr } = editor.state
              tr.setNodeMarkup(pos(), undefined, {
                ...current.attrs,
                ...patch,
              })
              editor.view.dispatch(tr)
            },
            remove: () => {
              editor
                .chain()
                .focus()
                .deleteRange({ from: pos(), to: pos() + node.nodeSize })
                .run()
            },
            swap: (mode: SwapMode) => options.onSwap(String(current.attrs.block_id), mode),
            setLocked: (locked: boolean) => {
              const { tr } = editor.state
              tr.setNodeMarkup(pos(), undefined, { ...current.attrs, locked })
              editor.view.dispatch(tr)
            },
            move: (dir: -1 | 1) => moveBlock(editor, pos(), node.nodeSize, dir),
            addBelow: () => options.onAddBelow(pos() + node.nodeSize),
            // Tier 3 (ADR-0021): the block becomes teacher-owned text, one undo step.
            convert: async () => {
              const out = await convertToFreeform(store_value())
              const block = freeformNode()
              const json = {
                ...block,
                attrs: {
                  ...block.attrs,
                  marks: out.marks,
                  answer: out.answer,
                  remark: current.attrs.remark ?? null,
                },
                content: out.content,
              }
              const { tr, schema } = editor.state
              const from = pos()
              tr.replaceWith(from, from + node.nodeSize, schema.nodeFromJSON(json))
              editor.view.dispatch(tr)
              if (out.dropped.length) {
                options.onNotice(`Converted to free-form. Not included: ${out.dropped.join('; ')}.`)
              }
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
          return true
        },
        // The Svelte component owns all interaction inside the block.
        stopEvent: () => true,
        ignoreMutation: () => true,
        destroy() {
          void unmount(component)
        },
      }
    }
  },
})

/** P8d: whether the generator filled this block (it can be swapped) and whether it's locked. */
export interface PaperSlot {
  generated: boolean
  locked: boolean
}

export function slotOf(attrs: Record<string, unknown>): PaperSlot {
  // Any generated question, slot or not: "Regenerate unlocked" refills it, so it can be
  // locked (and swapped) too. A bank question is never touched, so it gets neither.
  return {
    generated: isGeneratedPosition({ type: 'templatedQuestion', attrs }),
    locked: attrs.locked === true,
  }
}

/** Swap a block with its previous/next sibling. */
export function moveBlock(
  editor: NodeViewRendererProps['editor'],
  pos: number,
  size: number,
  dir: -1 | 1,
) {
  const { doc, tr } = editor.state
  const $pos = doc.resolve(pos)
  const index = $pos.index()
  const parent = $pos.parent
  const target = index + dir
  if (target < 0 || target >= parent.childCount) return
  const node = parent.child(index)
  const sibling = parent.child(target)
  if (dir === -1) {
    const from = pos - sibling.nodeSize
    tr.delete(pos, pos + size).insert(from, node)
  } else {
    tr.insert(pos + size + sibling.nodeSize, node).delete(pos, pos + size)
  }
  editor.view.dispatch(tr)
}

/** Build the node JSON for a freshly inserted question. */
export function questionNode(question: Question) {
  return {
    type: 'templatedQuestion',
    attrs: { block_id: newBlockId(), question },
  }
}
