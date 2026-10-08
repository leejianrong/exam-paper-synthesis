// The `templatedQuestion` TipTap node (ADR-0021): an atom holding a frozen canonical
// snapshot. Its node view mounts a Svelte component into the node's DOM — the one
// integration the plan flagged as a spike (Svelte 5 inside a ProseMirror node view).

import { Node } from '@tiptap/core'
import type { NodeViewRendererProps } from '@tiptap/core'
import { mount, unmount } from 'svelte'
import { writable } from 'svelte/store'
import type { Question } from '../types'
import QuestionBlock from './QuestionBlock.svelte'
import { newBlockId } from './doc'

export interface TemplatedQuestionOptions {
  /** Open the "add question" picker to insert after the block at `pos`. */
  onAddBelow: (afterPos: number) => void
}

export const TemplatedQuestion = Node.create<TemplatedQuestionOptions>({
  name: 'templatedQuestion',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: false,

  addOptions() {
    return { onAddBelow: () => {} }
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
          },
        },
      })

      return {
        dom,
        update(updated) {
          if (updated.type !== node.type) return false
          store.set(updated.attrs.question as Question)
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
function moveBlock(editor: NodeViewRendererProps['editor'], pos: number, size: number, dir: -1 | 1) {
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
