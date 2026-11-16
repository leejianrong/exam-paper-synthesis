// The P7 page blocks: `coverPage` (the paper's cover, always the first block) and `blankPage`
// (a page of its own: "intentionally left blank" or rough work). Both are atoms edited through
// small forms in their node views. The cover's time, total and examiner's table are derived by
// the engine when it prints, so the editor never asks for them.
import { Node } from '@tiptap/core'
import type { NodeViewRendererProps } from '@tiptap/core'
import type { Node as PMNode } from '@tiptap/pm/model'
import { Plugin, PluginKey } from '@tiptap/pm/state'

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

function labelled(label: string, el: HTMLElement, cls = 'page-field') {
  const wrap = document.createElement('label')
  wrap.className = cls
  wrap.append(label, el)
  return wrap
}

export const CoverPage = Node.create({
  name: 'coverPage',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: false, // it always stays first

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
    return (props: NodeViewRendererProps) => {
      const view = formView(props)
      const dom = document.createElement('div')
      dom.className = 'page-block cover-block'
      dom.setAttribute('data-cover-page', '')

      const heading = document.createElement('p')
      heading.className = 'page-block-title'
      heading.textContent = 'Cover page'

      const grid = document.createElement('div')
      grid.className = 'cover-grid'
      const inputs = new Map<string, HTMLInputElement>()
      for (const f of COVER_FIELDS) {
        const input = document.createElement('input')
        input.placeholder = f.placeholder
        input.maxLength = f.max
        input.setAttribute('aria-label', `Cover ${f.label.toLowerCase()}`)
        input.addEventListener('input', () =>
          view.setAttr({ [f.key]: f.key === 'date' ? input.value || null : input.value }),
        )
        inputs.set(f.key, input)
        grid.append(labelled(f.label, input))
      }

      const instructions = document.createElement('textarea')
      instructions.className = 'cover-instructions-input'
      instructions.rows = 3
      instructions.maxLength = 2000
      instructions.placeholder =
        'Instructions to candidates, one per line (optional). Write NOT in capitals to print it bold and underlined.'
      instructions.setAttribute('aria-label', 'Cover instructions')
      instructions.addEventListener('input', () =>
        view.setAttr({ instructions: instructions.value || null }),
      )

      const table = document.createElement('input')
      table.type = 'checkbox'
      table.setAttribute('aria-label', "For examiner's use table")
      table.addEventListener('change', () => view.setAttr({ examiner_table: table.checked }))
      // EXA-140: off unless chosen, so both store an explicit true/false once touched.
      const switches = COVER_SWITCHES.map((sw) => {
        const box = document.createElement('input')
        box.type = 'checkbox'
        box.setAttribute('aria-label', sw.label)
        box.addEventListener('change', () => view.setAttr({ [sw.key]: box.checked }))
        return { ...sw, box }
      })

      const note = document.createElement('p')
      note.className = 'page-block-note'
      note.textContent =
        'Time, question count, total marks, the examiner’s table and the page count come from the paper. The cover replaces the paper’s header and is left out of the answer key.'

      dom.append(
        heading,
        grid,
        instructions,
        labelled("For examiner's use table", table, 'page-field inline'),
        ...switches.map((sw) => labelled(sw.label, sw.box, 'page-field inline')),
        note,
      )

      const sync = () => {
        const a = view.node.attrs
        for (const [key, input] of inputs) view.set(input, String(a[key] ?? ''))
        view.set(instructions, String(a.instructions ?? ''))
        table.checked = a.examiner_table !== false
        for (const sw of switches) sw.box.checked = a[sw.key] === true
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
