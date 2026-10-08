// A hard page break (atom). Shown as a dashed rule in the editor; the server renders it
// as a CSS page break in the PDF.
import { Node } from '@tiptap/core'

export const PageBreak = Node.create({
  name: 'pageBreak',
  group: 'block',
  atom: true,
  selectable: true,
  parseHTML() {
    return [{ tag: 'div[data-page-break]' }]
  },
  renderHTML() {
    return ['div', { 'data-page-break': '', class: 'page-break-marker' }, 'page break']
  },
})
