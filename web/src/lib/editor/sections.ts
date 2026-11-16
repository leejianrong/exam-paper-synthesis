// The `section` TipTap node (P4): a divider atom that starts a paper section (title,
// instructions, mode, marks target). Questions after it belong to it until the next one. The
// range and marks beside the title are derived from the document, never typed, so they cannot
// drift from the questions (the engine's `paper_outline` computes the same for the PDF).
import { Node } from '@tiptap/core'
import type { NodeViewRendererProps } from '@tiptap/core'
import type { Node as PMNode } from '@tiptap/pm/model'
import { derived, writable, type Readable } from 'svelte/store'
import { get } from 'svelte/store'
import type { SectionInfo, SectionMode, SectionPlacement } from './doc'
import { DEFAULT_PLACEMENT, paperPlacement } from './layout'
import { paperSettings } from './paperSettings'

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

/** The marking margin: the section's own choice, else on for working sections (engine mirror). */
export function markingOn(attrs: { marking?: unknown; mode?: unknown }): boolean {
  if (typeof attrs.marking === 'boolean') return attrs.marking
  return attrs.mode === 'short' || attrs.mode === 'structured'
}

export const PLACEMENT_LABELS: Record<SectionPlacement, string> = {
  none: 'In the header only',
  question: 'Beside each question',
  answer: 'After each Ans: line',
  both: 'Beside the question and after Ans:',
}

/** Where the section's [n] print: its own choice, else none for MCQ and short-answer sections
 * (the header sentence gives the marks), else the paper-wide setting (engine mirror, EXA-139). */
export function sectionPlacement(
  attrs: { marks_placement?: unknown; mode?: unknown },
  paper: SectionPlacement,
): SectionPlacement {
  const chosen = attrs.marks_placement
  if (typeof chosen === 'string' && chosen in PLACEMENT_LABELS) return chosen as SectionPlacement
  return attrs.mode === 'mcq' || attrs.mode === 'short' ? 'none' : paper
}

/** Each top-level block's effective marks placement, in document order: the placement of the
 * section it sits in, or the paper's before the first section (the engine's render loop). */
export function blockPlacements(
  blocks: ReadonlyArray<{ type: string; attrs?: Record<string, unknown> | null }>,
  paper: SectionPlacement,
): SectionPlacement[] {
  let current = paper
  return blocks.map((b) =>
    b.type === 'section' ? (current = sectionPlacement(b.attrs ?? {}, paper)) : current,
  )
}

/** The top-level blocks' types and attrs, refreshed once per doc change by the Section extension. */
const docBlocks = writable<Array<{ type: string; attrs: Record<string, unknown> }>>([])

/** Every top-level block's placement, recomputed once per doc or paper-setting change and read by
 * the question node views, so each question shows its [n] exactly as it will print (EXA-152). */
export const placements: Readable<{ paper: SectionPlacement; blocks: SectionPlacement[] }> = derived(
  [docBlocks, paperSettings],
  ([blocks, settings]) => {
    const paper = paperPlacement(settings)
    return { paper, blocks: blockPlacements(blocks, paper) }
  },
)

function publishBlocks(doc: PMNode) {
  const blocks: Array<{ type: string; attrs: Record<string, unknown> }> = []
  doc.forEach((child) => blocks.push({ type: child.type.name, attrs: child.attrs }))
  docBlocks.set(blocks)
}

/** Follow the placement of the block at `getPos()` (a question, or a part inside one): calls
 * `apply` now and whenever it changes. `refresh` re-reads it after the node view moved. */
export function trackPlacement(
  editor: { state: { doc: PMNode } },
  getPos: () => number | undefined,
  apply: (p: SectionPlacement) => void,
): { refresh: () => void; current: () => SectionPlacement; destroy: () => void } {
  let state = { paper: DEFAULT_PLACEMENT as SectionPlacement, blocks: [] as SectionPlacement[] }
  let last: SectionPlacement | null = null
  const read = (): SectionPlacement => {
    try {
      const pos = getPos()
      if (typeof pos !== 'number') return state.paper
      return state.blocks[editor.state.doc.resolve(pos).index(0)] ?? state.paper
    } catch {
      return state.paper // the node view is being torn down
    }
  }
  const refresh = () => {
    const p = read()
    if (p !== last) {
      last = p
      apply(p)
    }
  }
  const destroy = placements.subscribe((v) => {
    state = v
    refresh()
  })
  return { refresh, current: () => last ?? state.paper, destroy }
}

export const Section = Node.create({
  name: 'section',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: true,

  onCreate() {
    publishBlocks(this.editor.state.doc)
  },

  onUpdate() {
    publishBlocks(this.editor.state.doc)
  },

  onDestroy() {
    docBlocks.set([])
  },

  addAttributes() {
    return {
      title: { default: '' },
      instructions: { default: null },
      mode: { default: null },
      marks_target: { default: null },
      marking: { default: null }, // marking margin; null follows the mode (P6a)
      marks_placement: { default: null }, // where the [n] print; null follows the mode (EXA-139)
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

      const marking = document.createElement('input')
      marking.type = 'checkbox'
      marking.setAttribute('aria-label', 'Marking margin')
      marking.addEventListener('change', () => setAttr({ marking: marking.checked }))

      const placement = document.createElement('select')
      placement.setAttribute('aria-label', 'Marks shown')
      placement.add(new Option('', ''))
      for (const [value, label] of Object.entries(PLACEMENT_LABELS)) placement.add(new Option(label, value))
      placement.addEventListener('change', () => setAttr({ marks_placement: placement.value || null }))

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
      row.append(title, field('Mode', mode), field('Target marks', target), field('Marks shown', placement), field('Marking margin', marking))
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
        marking.checked = markingOn(a)
        // The unset choice is labelled with what it means for this section's mode.
        const paper = get(paperSettings).marks_placement ?? DEFAULT_PLACEMENT
        placement.options[0].text = `Default: ${PLACEMENT_LABELS[sectionPlacement({ mode: a.mode }, paper)].toLowerCase()}`
        set(placement, String(a.marks_placement ?? ''))
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

export function sectionNode(
  title: string,
  opts: { mode?: SectionMode; marks_target?: number; instructions?: string } = {},
) {
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
