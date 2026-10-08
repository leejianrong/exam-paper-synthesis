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

export interface TemplatedQuestionOptions {
  /** Open the "add question" picker to insert after the block at `pos`. */
  onAddBelow: (afterPos: number) => void
  /** A message for the page (e.g. which figure a conversion had to drop). */
  onNotice: (message: string) => void
}

export const TemplatedQuestion = Node.create<TemplatedQuestionOptions>({
  name: 'templatedQuestion',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: false,

  addOptions() {
    return { onAddBelow: () => {}, onNotice: () => {} }
  },

  addAttributes() {
    return {
      block_id: { default: null },
      question: { default: null },
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
          ctx: {
            replace: (q: Question) => {
              const { tr } = editor.state
              tr.setNodeMarkup(pos(), undefined, { ...node.attrs, question: q })
              editor.view.dispatch(tr)
            },
            remove: () => {
              editor.chain().focus().deleteRange({ from: pos(), to: pos() + node.nodeSize }).run()
            },
            move: (dir: -1 | 1) => moveBlock(editor, pos(), node.nodeSize, dir),
            addBelow: () => options.onAddBelow(pos() + node.nodeSize),
            // Tier 3 (ADR-0021): the block becomes teacher-owned text, one undo step.
            convert: async () => {
              const out = await convertToFreeform(store_value())
              const block = freeformNode()
              const json = {
                ...block,
                attrs: { ...block.attrs, marks: out.marks, answer: out.answer },
                content: out.content,
              }
              const { tr, schema } = editor.state
              const from = pos()
              tr.replaceWith(from, from + node.nodeSize, schema.nodeFromJSON(json))
              editor.view.dispatch(tr)
              if (out.dropped.length) {
                options.onNotice(
                  `Converted to free-form. Not included: ${out.dropped.join('; ')}.`,
                )
              }
            },
          },
        },
      })

      return {
        dom,
        update(updated) {
          if (updated.type !== node.type) return false
          latest = updated.attrs.question as Question
          store.set(latest)
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

/** Swap a block with its previous/next sibling. */
export function moveBlock(editor: NodeViewRendererProps['editor'], pos: number, size: number, dir: -1 | 1) {
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
  return { type: 'templatedQuestion', attrs: { block_id: newBlockId(), question } }
}
