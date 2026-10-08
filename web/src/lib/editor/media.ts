// The `image` and `math` TipTap nodes (W2b) and the paste/drop upload extension.
//
// `image` is a block atom (group `media`, so it can sit at the top level, in a free-form
// body or in an answer — never inside list items, matching the document schema). `math` is
// an inline atom holding a LaTeX string, typeset by KaTeX and edited in a popover.

import { Extension, Node } from '@tiptap/core'
import type { Editor, NodeViewRendererProps } from '@tiptap/core'
import { Plugin } from '@tiptap/pm/state'
import { assetUrl, imageFiles, uploadAsset, type AssetMeta } from './assets'
import { mountMath } from './math'
import { openMathEditor } from './mathEditor'

function el<K extends keyof HTMLElementTagNameMap>(tag: K, cls: string, text?: string) {
  const e = document.createElement(tag)
  e.className = cls
  if (text !== undefined) e.textContent = text
  return e
}

const clampWidth = (raw: string): number => {
  const n = Math.round(Number(raw))
  return Number.isFinite(n) ? Math.min(100, Math.max(10, n)) : 100
}

export const ImageBlock = Node.create({
  name: 'image',
  group: 'media',
  atom: true,
  selectable: true,
  draggable: true,

  addAttributes() {
    return {
      asset_id: {
        default: null,
        parseHTML: (e: HTMLElement) => e.getAttribute('data-asset-id'),
        renderHTML: (a: Record<string, unknown>) => ({ 'data-asset-id': a.asset_id as string }),
      },
      alt: { default: '' },
      width_pct: { default: 100 },
    }
  },

  // Only our own images parse back in (copy/paste inside the editor); a foreign <img> —
  // a Word/Docs paste with data: or blob: sources — matches nothing and is dropped.
  parseHTML() {
    return [{ tag: 'img[data-asset-id]' }]
  },

  renderHTML({ HTMLAttributes, node }) {
    return [
      'img',
      {
        ...HTMLAttributes,
        src: assetUrl(String(node.attrs.asset_id)),
        alt: node.attrs.alt ?? '',
        style: `width:${node.attrs.width_pct}%`,
      },
    ]
  },

  addNodeView() {
    return ({ node, getPos, editor }: NodeViewRendererProps) => {
      let current = node
      const dom = el('figure', 'doc-image-node')
      const img = el('img', 'doc-image-img')
      const bar = el('div', 'doc-image-bar')
      bar.contentEditable = 'false'
      bar.hidden = true

      const widthLabel = el('label', '', 'Width ')
      const width = el('input', 'doc-image-width')
      width.type = 'number'
      width.min = '10'
      width.max = '100'
      width.step = '5'
      width.setAttribute('aria-label', 'Image width (%)')
      widthLabel.append(width, ' %')
      const altLabel = el('label', 'doc-image-alt-label', 'Description ')
      const alt = el('input', 'doc-image-alt')
      alt.type = 'text'
      alt.maxLength = 300
      alt.placeholder = 'For screen readers'
      alt.setAttribute('aria-label', 'Image description')
      altLabel.append(alt)
      const remove = el('button', 'danger', 'Remove')
      remove.type = 'button'
      bar.append(widthLabel, altLabel, remove)
      dom.append(img, bar)

      const update = (attrs: Record<string, unknown>) => {
        const pos = getPos()
        if (typeof pos !== 'number') return
        const { tr } = editor.state
        tr.setNodeMarkup(pos, undefined, { ...current.attrs, ...attrs })
        editor.view.dispatch(tr)
      }
      width.addEventListener('change', () => update({ width_pct: clampWidth(width.value) }))
      alt.addEventListener('change', () => update({ alt: alt.value }))
      remove.addEventListener('click', () => {
        const pos = getPos()
        if (typeof pos === 'number') {
          editor.chain().focus().deleteRange({ from: pos, to: pos + current.nodeSize }).run()
        }
      })

      const sync = () => {
        img.src = assetUrl(String(current.attrs.asset_id))
        img.alt = String(current.attrs.alt ?? '')
        img.style.width = `${current.attrs.width_pct}%`
        if (document.activeElement !== width) width.value = String(current.attrs.width_pct)
        if (document.activeElement !== alt) alt.value = String(current.attrs.alt ?? '')
      }
      sync()

      return {
        dom,
        update(updated) {
          if (updated.type !== node.type) return false
          current = updated
          sync()
          return true
        },
        // The popover is shown only while the figure is selected, so it never prints or clutters.
        selectNode() {
          dom.classList.add('selected')
          bar.hidden = false
        },
        deselectNode() {
          dom.classList.remove('selected')
          bar.hidden = true
        },
        stopEvent: (event) => bar.contains(event.target as globalThis.Node),
        ignoreMutation: () => true,
      }
    }
  },
})

export const MathNode = Node.create({
  name: 'math',
  group: 'inline',
  inline: true,
  atom: true,
  selectable: true,

  addAttributes() {
    return {
      latex: {
        default: '',
        parseHTML: (e: HTMLElement) => e.getAttribute('data-math') ?? '',
        renderHTML: (a: Record<string, unknown>) => ({ 'data-math': a.latex as string }),
      },
    }
  },

  parseHTML() {
    return [{ tag: 'span[data-math]' }]
  },

  renderHTML({ HTMLAttributes, node }) {
    return ['span', { ...HTMLAttributes, class: 'math-host' }, `\\(${node.attrs.latex}\\)`]
  },

  addNodeView() {
    return ({ node, getPos, editor }: NodeViewRendererProps) => {
      let current = node
      const dom = el('span', 'math-host math-node')
      dom.setAttribute('role', 'button')
      dom.setAttribute('tabindex', '0')
      dom.title = 'Edit equation'
      void mountMath(dom, String(node.attrs.latex))

      const edit = () => {
        openMathEditor({
          latex: String(current.attrs.latex),
          apply: (latex) => {
            const pos = getPos()
            if (typeof pos !== 'number') return
            const { tr } = editor.state
            if (latex === null || latex.trim() === '') tr.delete(pos, pos + current.nodeSize)
            else tr.setNodeMarkup(pos, undefined, { latex })
            editor.view.dispatch(tr)
          },
        })
      }
      dom.addEventListener('click', edit)
      dom.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') edit()
      })

      return {
        dom,
        update(updated) {
          if (updated.type !== node.type) return false
          current = updated
          void mountMath(dom, String(updated.attrs.latex))
          return true
        },
        stopEvent: () => false,
        ignoreMutation: () => true,
      }
    }
  },
})

/**
 * Insert `node` (a block) after the textblock holding the caret — or in place of it when it
 * is empty — at the nearest level whose parent accepts it. Falls back to the end of the doc.
 */
export function insertBlock(editor: Editor, node: { type: string; attrs?: Record<string, unknown> }) {
  const { state } = editor
  const type = state.schema.nodes[node.type]
  const $from = state.selection.$from
  let from: number | null = null
  let to: number | null = null
  for (let d = $from.depth; d > 0; d--) {
    const parent = $from.node(d - 1)
    const index = $from.indexAfter(d - 1)
    if (parent.canReplaceWith(index, index, type)) {
      const textblock = $from.node(d)
      const empty = d === $from.depth && textblock.type.name === 'paragraph' && textblock.content.size === 0
      from = empty ? $from.before(d) : $from.after(d)
      to = empty ? $from.after(d) : from
      break
    }
  }
  if (from === null || to === null) from = to = state.doc.content.size
  editor.chain().insertContentAt({ from, to }, node).run()
}

export interface ImageUploadOptions {
  upload: (file: File) => Promise<AssetMeta>
  onError: (message: string) => void
}

/** Upload each file, then insert it as an `image` block; a failure is reported, not thrown. */
export async function uploadAndInsert(editor: Editor, files: File[], options: ImageUploadOptions) {
  for (const file of files) {
    try {
      const meta = await options.upload(file)
      insertBlock(editor, { type: 'image', attrs: { asset_id: meta.id, alt: '', width_pct: 100 } })
    } catch (e) {
      options.onError(e instanceof Error ? e.message : String(e))
    }
  }
}

/** Paste and drop of PNG/JPEG files: upload first, then insert an `image` node. */
export const ImageUpload = Extension.create<ImageUploadOptions>({
  name: 'imageUpload',

  addOptions() {
    return {
      upload: (file: File) => uploadAsset(file, file.name),
      onError: () => {},
    }
  },

  addProseMirrorPlugins() {
    const { editor } = this
    const options = this.options
    const run = (files: File[]) => uploadAndInsert(editor, files, options)
    return [
      new Plugin({
        props: {
          handlePaste(_view, event) {
            const files = imageFiles(event.clipboardData)
            // Text on the clipboard wins (Word puts an image preview beside the text).
            if (!files.length || event.clipboardData?.getData('text/plain')) return false
            event.preventDefault()
            void run(files)
            return true
          },
          handleDrop(view, event) {
            const files = imageFiles(event.dataTransfer)
            if (!files.length) return false
            event.preventDefault()
            const at = view.posAtCoords({ left: event.clientX, top: event.clientY })
            if (at) editor.commands.setTextSelection(at.pos)
            void run(files)
            return true
          },
        },
      }),
    ]
  },
})
