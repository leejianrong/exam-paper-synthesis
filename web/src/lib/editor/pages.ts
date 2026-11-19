// The P7 page blocks: `coverPage` (the paper's cover, always the first block) and `blankPage`
// (a page of its own: "intentionally left blank" or rough work). Both are atoms. The blank page
// is edited through a small form in its node view; the cover shows as a compact card and its
// fields edit in the side panel (EXA-164, `CoverSettings.svelte`). The cover's time, total and
// examiner's table are derived by the engine when it prints, so the editor never asks for them.
import { Node } from '@tiptap/core'
import type { NodeViewRendererProps } from '@tiptap/core'
import type { Node as PMNode } from '@tiptap/pm/model'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import { editButton, isEditButton, settingsShortcut, type OpenSettings } from './blockSettings'

export type BlankKind = 'blank' | 'rough'

export const BLANK_TEXT: Record<BlankKind, string> = {
  blank: 'This page is intentionally left blank.',
  rough: 'Rough work',
}

/** The cover's text fields, in form order (all optional strings). */
export const COVER_FIELDS = [
  { key: 'school', label: 'School', placeholder: 'e.g. Pandan Primary School', max: 120 },
  { key: 'exam', label: 'Exam', placeholder: 'e.g. Preliminary Examination (2026)', max: 120 },
  { key: 'level', label: 'Level', placeholder: 'e.g. Primary 6', max: 60 },
  { key: 'subject', label: 'Subject', placeholder: 'Mathematics', max: 60 },
  { key: 'paper', label: 'Paper', placeholder: 'e.g. Paper 1 (Booklet A)', max: 120 },
  { key: 'date', label: 'Date', placeholder: 'optional, printed as written', max: 60 },
] as const

/** The cover's off-by-default switches (EXA-140). */
export const COVER_SWITCHES = [
  { key: 'parent_signature', label: "Parent's signature line" },
  { key: 'even_pages', label: 'Pad to an even number of pages' },
] as const

/** True when a document's cover, if any, is its first block and the only one (engine rule). */
export function coverPlacementOk(doc: PMNode): boolean {
  // Count covers at any depth: one pasted into a list item would be refused by the server too.
  let covers = 0
  doc.descendants((node) => {
    if (node.type.name === 'coverPage') covers += 1
    return true
  })
  return covers === 0 || (covers === 1 && doc.firstChild?.type.name === 'coverPage')
}

export function hasCover(doc: PMNode): boolean {
  return doc.firstChild?.type.name === 'coverPage'
}

type InputLike = HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement

function isFormTarget(event: Event): boolean {
  const t = event.target as HTMLElement | null
  return !!t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT')
}

/** Shared node-view plumbing: write attrs back and never clobber a field being typed in. */
function formView(props: NodeViewRendererProps) {
  let current = props.node
  const setAttr = (attrs: Record<string, unknown>) => {
    const pos = props.getPos()
    if (typeof pos !== 'number') return
    const { tr } = props.editor.state
    tr.setNodeMarkup(pos, undefined, { ...current.attrs, ...attrs })
    props.editor.view.dispatch(tr)
  }
  const set = (el: InputLike, v: string) => {
    if (document.activeElement !== el && el.value !== v) el.value = v
  }
  return {
    get node() {
      return current
    },
    setNode(n: PMNode) {
      current = n
    },
    setAttr,
    set,
  }
}

function labelled(label: string, el: HTMLElement) {
  const wrap = document.createElement('label')
  wrap.className = 'page-field'
  wrap.append(label, el)
  return wrap
}

export interface CoverOptions {
  /** Opens the cover's settings in the side panel (EXA-164). */
  onEdit: OpenSettings | null
}

/** The cover card's lines, as the printed cover leads with them: school, exam, then level,
 *  subject and paper on one line. Empty lines are left out. */
export function coverLines(a: Record<string, unknown>): string[] {
  const text = (k: string) => (typeof a[k] === 'string' ? (a[k] as string).trim() : '')
  const meta = ['level', 'subject', 'paper'].map(text).filter(Boolean).join(' · ')
  return [text('school'), text('exam'), meta].filter(Boolean)
}

export const CoverPage = Node.create<CoverOptions>({
  name: 'coverPage',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: false, // it always stays first

  addOptions() {
    return { onEdit: null }
  },

  addAttributes() {
    return {
      school: { default: '' },
      exam: { default: '' },
      level: { default: '' },
      subject: { default: 'Mathematics' },
      paper: { default: '' },
      date: { default: null },
      instructions: { default: null },
      examiner_table: { default: null }, // null = on
      parent_signature: { default: null }, // null = off (EXA-140)
      even_pages: { default: null }, // null = off: pad to an even page count (EXA-140)
    }
  },

  parseHTML() {
    return [{ tag: 'div[data-cover-page]' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', { 'data-cover-page': '', ...HTMLAttributes }]
  },

  addKeyboardShortcuts() {
    return { 'Alt-Enter': () => settingsShortcut(this.editor, this.name, this.options.onEdit) }
  },

  addProseMirrorPlugins() {
    // A cover anywhere but first would be refused by the server: refuse it here instead.
    return [
      new Plugin({
        key: new PluginKey('coverFirst'),
        filterTransaction: (tr) => !tr.docChanged || coverPlacementOk(tr.doc),
      }),
    ]
  },

  addNodeView() {
    const options = this.options
    return (props: NodeViewRendererProps) => {
      let current = props.node
      const dom = document.createElement('div')
      dom.className = 'cover-block'
      dom.setAttribute('data-cover-page', '')

      const caption = document.createElement('p')
      caption.className = 'cover-caption'
      caption.textContent = 'Cover page'
      const head = document.createElement('div')
      head.className = 'cover-head'
      head.append(caption)
      if (options.onEdit) {
        head.append(
          editButton('cover page', () => {
            const pos = props.getPos()
            if (typeof pos === 'number') options.onEdit?.(pos)
          }),
        )
      }
      const body = document.createElement('div')
      body.className = 'cover-lines'
      dom.append(head, body)

      const sync = () => {
        const lines = coverLines(current.attrs)
        body.replaceChildren(
          ...(lines.length ? lines : ['Add the school and exam']).map((t) => {
            const p = document.createElement('p')
            p.className = lines.length ? 'cover-line' : 'cover-line empty'
            p.textContent = t
            return p
          }),
        )
      }
      sync()

      return {
        dom,
        update(next: PMNode) {
          if (next.type !== current.type) return false
          current = next
          sync()
          return true
        },
        stopEvent: isEditButton,
        ignoreMutation: () => true,
      }
    }
  },
})

export const BlankPage = Node.create({
  name: 'blankPage',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: true,

  addAttributes() {
    return {
      kind: { default: 'blank' },
      text: { default: null },
    }
  },

  parseHTML() {
    return [{ tag: 'div[data-blank-page]' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', { 'data-blank-page': '', ...HTMLAttributes }]
  },

  addNodeView() {
    return (props: NodeViewRendererProps) => {
      const view = formView(props)
      const dom = document.createElement('div')
      dom.className = 'page-block blank-block'
      dom.setAttribute('data-blank-page', '')

      const heading = document.createElement('p')
      heading.className = 'page-block-title'
      heading.textContent = 'Page of its own'

      const kind = document.createElement('select')
      kind.setAttribute('aria-label', 'Blank page kind')
      kind.add(new Option('Left blank', 'blank'))
      kind.add(new Option('Rough work', 'rough'))
      kind.addEventListener('change', () => view.setAttr({ kind: kind.value }))

      const text = document.createElement('input')
      text.className = 'blank-text-input'
      text.maxLength = 200
      text.setAttribute('aria-label', 'Blank page wording')
      text.addEventListener('input', () => view.setAttr({ text: text.value || null }))

      const row = document.createElement('div')
      row.className = 'page-row'
      row.append(heading, labelled('Kind', kind), text)
      dom.append(row)

      const sync = () => {
        const a = view.node.attrs
        const k: BlankKind = a.kind === 'rough' ? 'rough' : 'blank'
        view.set(kind, k)
        text.placeholder = BLANK_TEXT[k]
        view.set(text, String(a.text ?? ''))
        dom.dataset.kind = k
      }
      sync()

      return {
        dom,
        update(next: PMNode) {
          if (next.type !== view.node.type) return false
          view.setNode(next)
          sync()
          return true
        },
        stopEvent: isFormTarget,
        ignoreMutation: () => true,
      }
    }
  },
})

export function coverNode(attrs: Record<string, unknown> = {}) {
  return { type: 'coverPage', attrs: { subject: 'Mathematics', ...attrs } }
}

export function blankPageNode(kind: BlankKind = 'blank', text: string | null = null) {
  return { type: 'blankPage', attrs: { kind, text } }
}
