// The `section` TipTap node (P4): a divider atom that starts a paper section (title,
// instructions, mode, marks target). Questions after it belong to it until the next one. The
// range and marks beside the title are derived from the document, never typed, so they cannot
// drift from the questions (the engine's `paper_outline` computes the same for the PDF).
import { Node } from '@tiptap/core'
import type { NodeViewRendererProps } from '@tiptap/core'
import { writable, type Readable } from 'svelte/store'
import type { SectionInfo, SectionMode } from './doc'

/** Derived section figures, set by the page and read by the node views (outside its tree). */
export const outline = writable<SectionInfo[]>([])

export const MODE_LABELS: Record<SectionMode, string> = {
  mcq: 'Multiple choice',
  short: 'Short answer',
  structured: 'Structured',
}

/** "Questions 2–3 · 5 / 10 marks", "Question 4 · 3 marks", or "No questions yet". */
export function sectionSummary(info: SectionInfo | undefined): string {
  if (!info || info.first === null) return 'No questions yet'
  const range =
    info.first === info.last ? `Question ${info.first}` : `Questions ${info.first}–${info.last}`
  const marks =
    info.target === null ? `${info.marks} marks` : `${info.marks} / ${info.target} marks`
  return `${range} · ${marks}`
}

/** 'over' / 'under' when a target is set and the marks differ from it, else 'ok'. */
export function targetState(info: SectionInfo | undefined): 'ok' | 'over' | 'under' {
  if (!info || info.target === null || info.first === null) return 'ok'
  return info.marks > info.target ? 'over' : info.marks < info.target ? 'under' : 'ok'
}

export const Section = Node.create({
  name: 'section',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: true,

  addAttributes() {
    return {
      title: { default: '' },
      instructions: { default: null },
      mode: { default: null },
      marks_target: { default: null },
    }
  },

  parseHTML() {
    return [{ tag: 'div[data-section]' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', { 'data-section': '', ...HTMLAttributes }]
  },

  addNodeView() {
    return ({ node, getPos, editor }: NodeViewRendererProps) => {
      let current = node
      const dom = document.createElement('div')
      dom.className = 'section-block'
      dom.setAttribute('data-section', '')

      const setAttr = (attrs: Record<string, unknown>) => {
        const pos = getPos()
        if (typeof pos !== 'number') return
        const { tr } = editor.state
        tr.setNodeMarkup(pos, undefined, { ...current.attrs, ...attrs })
        editor.view.dispatch(tr)
      }

      const field = (label: string, el: HTMLElement) => {
        const wrap = document.createElement('label')
        wrap.className = 'section-field'
        wrap.append(label, el)
        return wrap
      }

      const title = document.createElement('input')
      title.className = 'section-title-input'
      title.placeholder = 'Section title, e.g. Booklet A'
      title.setAttribute('aria-label', 'Section title')
      title.maxLength = 120
      title.addEventListener('input', () => setAttr({ title: title.value }))

      const mode = document.createElement('select')
      mode.setAttribute('aria-label', 'Section mode')
      mode.add(new Option('no mode', ''))
      for (const [value, label] of Object.entries(MODE_LABELS)) mode.add(new Option(label, value))
      mode.addEventListener('change', () => setAttr({ mode: mode.value || null }))

      const target = document.createElement('input')
      target.type = 'number'
      target.min = '0'
      target.max = '500'
      target.className = 'section-target-input'
      target.setAttribute('aria-label', 'Marks target')
      target.addEventListener('input', () => {
        const n = target.value === '' ? null : Math.max(0, Math.min(500, Math.round(+target.value)))
        setAttr({ marks_target: n })
      })

      const instructions = document.createElement('textarea')
      instructions.className = 'section-instructions-input'
      instructions.rows = 2
      instructions.maxLength = 1000
      instructions.placeholder = 'Instructions for students (optional)'
      instructions.setAttribute('aria-label', 'Section instructions')
      instructions.addEventListener('input', () => setAttr({ instructions: instructions.value }))

      const summary = document.createElement('p')
      summary.className = 'section-summary'
      summary.setAttribute('role', 'status')

      const row = document.createElement('div')
      row.className = 'section-row'
      row.append(title, field('Mode', mode), field('Target marks', target))
      dom.append(row, instructions, summary)

      const sync = () => {
        const a = current.attrs
        // Never overwrite a field the author is typing in.
        const set = (el: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement, v: string) => {
          if (document.activeElement !== el && el.value !== v) el.value = v
        }
        set(title, String(a.title ?? ''))
        set(mode, String(a.mode ?? ''))
        set(target, a.marks_target === null || a.marks_target === undefined ? '' : String(a.marks_target))
        set(instructions, String(a.instructions ?? ''))
      }

      const indexOfSelf = (): number => {
        const pos = getPos()
        if (typeof pos !== 'number') return -1
        let idx = -1
        editor.state.doc.forEach((child, offset) => {
          if (child.type.name === 'section' && offset <= pos) idx += 1
        })
        return idx
      }

      const render = (all: SectionInfo[]) => {
        const info = all[indexOfSelf()]
        summary.textContent = sectionSummary(info)
        summary.dataset.state = targetState(info)
      }
      const unsubscribe = (outline as Readable<SectionInfo[]>).subscribe(render)

      sync()
      render([])

      return {
        dom,
        update(next) {
          if (next.type !== current.type) return false
          current = next
          sync()
          return true
        },
        stopEvent: (event: Event) => {
          const t = event.target as HTMLElement | null
          return !!t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT')
        },
        ignoreMutation: () => true,
        destroy: unsubscribe,
      }
    }
  },
})

export function sectionNode(title: string, opts: { mode?: SectionMode; marks_target?: number; instructions?: string } = {}) {
  return {
    type: 'section',
    attrs: {
      title,
      instructions: opts.instructions ?? null,
      mode: opts.mode ?? null,
      marks_target: opts.marks_target ?? null,
    },
  }
}
