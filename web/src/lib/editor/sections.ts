// The `section` TipTap node (P4): a divider atom that starts a paper section (title,
// instructions, mode, marks target). Questions after it belong to it until the next one. The
// range and marks beside the title are derived from the document, never typed, so they cannot
// drift from the questions (the engine's `paper_outline` computes the same for the PDF).
// On the page it is a compact header; its settings edit in the side panel (EXA-164).
import { Node } from '@tiptap/core'
import type { NodeViewRendererProps } from '@tiptap/core'
import type { Node as PMNode } from '@tiptap/pm/model'
import { derived, writable, type Readable } from 'svelte/store'
import { SECTION_PLACEMENTS, type SectionInfo, type SectionMode, type SectionPlacement } from './doc'
import { DEFAULT_PLACEMENT, MARKS_SHOWN, paperPlacement } from './layout'
import { paperSettings } from './paperSettings'
import { editButton, isEditButton, settingsShortcut, type OpenSettings } from './blockSettings'

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

/** Where the section's [n] print: its own choice, else none for MCQ and short-answer sections
 * (the header sentence gives the marks), else the paper-wide setting (engine mirror, EXA-139). */
export function sectionPlacement(
  attrs: { marks_placement?: unknown; mode?: unknown },
  paper: SectionPlacement,
): SectionPlacement {
  const chosen = attrs.marks_placement
  if (SECTION_PLACEMENTS.includes(chosen as SectionPlacement)) return chosen as SectionPlacement
  return attrs.mode === 'mcq' || attrs.mode === 'short' ? 'none' : paper
}

const lower = (s: string) => s.charAt(0).toLowerCase() + s.slice(1)

/** The name of a section's unset "Marks shown" choice (EXA-164). */
export function sectionMarksDefault(mode: SectionMode | null): string {
  return mode === 'mcq' || mode === 'short' ? `${MODE_LABELS[mode]} default` : 'Same as the paper'
}

/** The line under a section's "Marks shown": what its choice comes to, against the paper's. */
export function sectionMarksNote(
  attrs: { marks_placement?: unknown; mode?: unknown },
  paper: SectionPlacement,
): string {
  const own = SECTION_PLACEMENTS.includes(attrs.marks_placement as SectionPlacement)
  const mode = attrs.mode as SectionMode
  if (own) return `Chosen for this section. The paper's: ${lower(MARKS_SHOWN[paper])}.`
  if (mode === 'mcq' || mode === 'short')
    return `${MODE_LABELS[mode]} keeps marks in the section header unless you choose.`
  return `Follows the paper: ${lower(MARKS_SHOWN[paper])}.`
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

export interface SectionOptions {
  /** Opens the section's settings in the side panel (EXA-164). */
  onEdit: OpenSettings | null
}

/** The n-th section of the document (0-based) for the section starting at `pos`, or -1. */
export function sectionIndexAt(doc: PMNode, pos: number): number {
  let idx = -1
  let found = -1
  doc.forEach((child, offset) => {
    if (child.type.name !== 'section') return
    idx += 1
    if (offset === pos) found = idx
  })
  return found
}

/** A generic title ("Section A", "Booklet 2", "Part B") is not printed: the engine's
 *  `_GENERIC_TITLE` (EXA-139). */
const GENERIC_TITLE = /^\s*(section|booklet|part)\s+([a-z]|\d{1,2})\s*$/i

/** Whether the section's title prints in the paper (a teacher's own title, not a generic one). */
export function titlePrints(title: unknown): boolean {
  const t = String(title ?? '').trim()
  return !!t && !GENERIC_TITLE.test(t)
}

/** The header's short cues: a generic title that won't print, the mode, and whether the marking
 *  margin is on. */
export function sectionCues(attrs: { title?: unknown; mode?: unknown; marking?: unknown }): string {
  const generic = String(attrs.title ?? '').trim() !== '' && !titlePrints(attrs.title)
  const mode = MODE_LABELS[attrs.mode as SectionMode] as string | undefined
  return [generic && 'title not printed', mode, markingOn(attrs) && 'marking margin']
    .filter(Boolean)
    .join(' · ')
}

export const Section = Node.create<SectionOptions>({
  name: 'section',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: true,

  addOptions() {
    return { onEdit: null }
  },

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

  addKeyboardShortcuts() {
    return { 'Alt-Enter': () => settingsShortcut(this.editor, this.name, this.options.onEdit) }
  },

  addNodeView() {
    const options = this.options
    return ({ node, getPos, editor }: NodeViewRendererProps) => {
      let current = node
      const dom = document.createElement('div')
      dom.className = 'section-block'
      dom.setAttribute('data-section', '')

      const title = document.createElement('h3')
      title.className = 'section-title'
      const summary = document.createElement('span')
      summary.className = 'section-summary'
      const cues = document.createElement('span')
      cues.className = 'section-cues'
      const head = document.createElement('div')
      head.className = 'section-head'
      head.append(title, summary, cues)
      if (options.onEdit) {
        head.append(
          editButton('section settings', () => {
            const pos = getPos()
            if (typeof pos === 'number') options.onEdit?.(pos)
          }),
        )
      }
      const instructions = document.createElement('p')
      instructions.className = 'section-instructions'
      dom.append(head, instructions)

      const sync = () => {
        const a = current.attrs
        const text = String(a.title ?? '').trim()
        title.textContent = text || 'Untitled section'
        // faint unless it prints: an empty or generic title is for the editor only
        title.classList.toggle('untitled', !titlePrints(text))

        cues.textContent = sectionCues(a)
        const instr = String(a.instructions ?? '').trim()
        instructions.textContent = instr
        instructions.hidden = !instr
      }

      const render = (all: SectionInfo[]) => {
        const pos = getPos()
        const info = typeof pos === 'number' ? all[sectionIndexAt(editor.state.doc, pos)] : undefined
        summary.textContent = sectionSummary(info)
        summary.dataset.state = targetState(info)
      }
      const unsubscribe = (outline as Readable<SectionInfo[]>).subscribe(render)

      sync()

      return {
        dom,
        update(next) {
          if (next.type !== current.type) return false
          current = next
          sync()
          return true
        },
        stopEvent: isEditButton,
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
