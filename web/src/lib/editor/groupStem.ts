// The `groupStem` TipTap node (EXA-90): a shared stem (text, a table as text, figures, equations)
// that the next `count` questions all refer to: "Use the table below to answer Questions 12 and
// 13." The questions stay ordinary top-level blocks with their own numbers, marks and answers, so
// numbering, sections and the key need nothing new; the stem only says how many follow it (the
// engine's `stem_members` reads the same rule). The lead line is derived from the numbers, never
// typed. On the page the stem's questions carry a bar down their left (a decoration).
import { Node } from '@tiptap/core'
import type { NodeViewRendererProps } from '@tiptap/core'
import type { Node as PMNode } from '@tiptap/pm/model'
import { Plugin, PluginKey, TextSelection, type EditorState, type Transaction } from '@tiptap/pm/state'
import { closeHistory, isHistoryTransaction } from '@tiptap/pm/history'
import { Decoration, DecorationSet } from '@tiptap/pm/view'
import { get } from 'svelte/store'
import { newBlockId } from './doc'
import { numberFrom } from './layout'
import { paperSettings } from './paperSettings'

export const GROUP_STEM = 'groupStem'
export const MAX_GROUP_COUNT = 20
const QUESTIONS = ['templatedQuestion', 'freeformQuestion']
/** A group never runs past these (engine `_GROUP_ENDS`). */
const ENDS = ['section', 'blankPage', 'coverPage', GROUP_STEM]

interface Block {
  type: string
  attrs?: Record<string, unknown> | null
}

/** Indexes of the questions sharing the stem at `blocks[at]`: the next `count` questions,
 *  rich text between them allowed; a section, blank page or another stem ends it early. */
export function stemMembers(blocks: ReadonlyArray<Block>, at: number): number[] {
  const want = Number(blocks[at]?.attrs?.count ?? 0)
  const out: number[] = []
  for (let i = at + 1; i < blocks.length && out.length < want; i++) {
    if (ENDS.includes(blocks[i].type)) break
    if (QUESTIONS.includes(blocks[i].type)) out.push(i)
  }
  return out
}

/** "Use the information below to answer Questions 12 and 13." (engine `stem_sentence`). */
export function stemSentence(numbers: number[]): string {
  if (!numbers.length) return ''
  const which =
    numbers.length === 1
      ? `Question ${numbers[0]}`
      : numbers.length === 2
        ? `Questions ${numbers[0]} and ${numbers[1]}`
        : `Questions ${numbers[0]} to ${numbers[numbers.length - 1]}`
  return `Use the information below to answer ${which}.`
}

function blocksOf(doc: PMNode): Block[] {
  const out: Block[] = []
  doc.forEach((c) => out.push({ type: c.type.name, attrs: c.attrs }))
  return out
}

/** The printed numbers of the questions sharing the stem at top-level index `at`. */
export function stemNumbers(doc: PMNode, at: number, start: number): number[] {
  const blocks = blocksOf(doc)
  const numberAt: number[] = []
  let n = start
  blocks.forEach((b, i) => {
    if (QUESTIONS.includes(b.type)) numberAt[i] = n++
  })
  return stemMembers(blocks, at).map((i) => numberAt[i])
}

/** A fresh stem for the next `count` questions (caret goes in its first paragraph). */
export function stemNode(count = 2) {
  return { type: GROUP_STEM, attrs: { block_id: newBlockId(), count }, content: [{ type: 'paragraph' }] }
}

/** The stem's own changes to its count: the membership plugin leaves them as they are. */
const OWN = 'groupStemCount'
const key = new PluginKey('groupStem')

/** Set the count of the stem at `pos` (a top-level offset), as its own undo step. */
export function setStemCount(state: EditorState, pos: number, count: number): Transaction | null {
  const node = state.doc.nodeAt(pos)
  if (!node || node.type.name !== GROUP_STEM || count < 1 || count > MAX_GROUP_COUNT) return null
  const tr = state.tr.setNodeMarkup(pos, undefined, { ...node.attrs, count })
  closeHistory(tr)
  return tr.setMeta(OWN, true)
}

/** Each stem's members (by block id) in a document, keyed by the stem's block id. */
function membership(doc: PMNode): Map<string, string[]> {
  const blocks = blocksOf(doc)
  const out = new Map<string, string[]>()
  blocks.forEach((b, i) => {
    if (b.type !== GROUP_STEM || !b.attrs?.block_id) return
    out.set(String(b.attrs.block_id), stemMembers(blocks, i).map((m) => String(blocks[m].attrs?.block_id)))
  })
  return out
}

/** The counts that keep each stem's questions with it after an edit: a deleted question leaves
 *  the group without pulling the next one in, and a new question inserted between two of its
 *  questions joins it. The group ends at the last of its old questions still there, and never
 *  grows past a question that was not one of them (an old question moved in from elsewhere, or a
 *  pasted copy, which keeps its original's id until the paper is saved). */
export function keepMembers(before: PMNode, after: PMNode): Array<{ pos: number; count: number }> {
  const old = membership(before)
  const existed = new Set<string>()
  before.forEach((c) => {
    if (QUESTIONS.includes(c.type.name)) existed.add(String(c.attrs.block_id))
  })
  const blocks = blocksOf(after)
  const fixes: Array<{ pos: number; count: number }> = []
  after.forEach((child, pos, i) => {
    if (child.type.name !== GROUP_STEM) return
    const was = old.get(String(child.attrs.block_id))
    if (!was) return
    let count = 0
    let seen = 0
    const met = new Set<string>()
    for (let j = i + 1; j < blocks.length && !ENDS.includes(blocks[j].type); j++) {
      if (!QUESTIONS.includes(blocks[j].type)) continue
      seen++
      const id = String(blocks[j].attrs?.block_id)
      const first = !met.has(id)
      met.add(id)
      if (first && was.includes(id)) count = seen
      else if (!first || existed.has(id)) break // not one of its questions: the group ends here
    }
    if (count > 0 && count !== child.attrs.count) fixes.push({ pos, count })
  })
  return fixes
}

/** Where moving the question at top-level index `index` steps it into or out of a group instead
 *  of past a neighbour: down from the last place of a group (it leaves the group, stays put), or
 *  up from just under a group (it joins). Null for an ordinary move. */
export function groupStep(doc: PMNode, index: number, dir: -1 | 1): { pos: number; count: number } | null {
  const blocks = blocksOf(doc)
  if (!QUESTIONS.includes(blocks[index]?.type)) return null
  const offsets: number[] = []
  doc.forEach((_c, p) => offsets.push(p))
  for (let at = 0; at < blocks.length; at++) {
    if (blocks[at].type !== GROUP_STEM) continue
    const members = stemMembers(blocks, at)
    const count = Number(blocks[at].attrs?.count)
    const pos = offsets[at]
    const last = members[members.length - 1]
    if (dir === 1 && last === index && members.length > 1) return { pos, count: members.length - 1 }
    if (dir === -1 && last !== undefined && members.length === count && count < MAX_GROUP_COUNT) {
      // the next question after the group, with only rich text between
      const next = blocks.findIndex((b, j) => j > last && (QUESTIONS.includes(b.type) || ENDS.includes(b.type)))
      if (next === index) return { pos, count: count + 1 }
    }
  }
  return null
}

function decorate(doc: PMNode): DecorationSet {
  const blocks = blocksOf(doc)
  const offsets: Array<{ pos: number; size: number }> = []
  doc.forEach((c, p) => offsets.push({ pos: p, size: c.nodeSize }))
  const decos: Decoration[] = []
  blocks.forEach((b, at) => {
    if (b.type !== GROUP_STEM) return
    const members = stemMembers(blocks, at)
    members.forEach((m, k) => {
      const { pos, size } = offsets[m]
      decos.push(Decoration.node(pos, pos + size, { class: k === members.length - 1 ? 'in-group group-last' : 'in-group' }))
    })
  })
  return DecorationSet.create(doc, decos)
}

export const GroupStem = Node.create({
  name: GROUP_STEM,
  // Its own group (not `block`), like a free-form question: a stem sits at the top level only.
  group: 'question',
  content: '(paragraph | bulletList | orderedList | image)+',
  isolating: true,
  defining: true,
  draggable: false,

  addAttributes() {
    return {
      block_id: { default: null },
      count: {
        default: 2,
        parseHTML: (el) => Number(el.getAttribute('data-count')) || 2,
        renderHTML: (a) => ({ 'data-count': String(a.count) }),
      },
    }
  },

  parseHTML() {
    return [{ tag: 'div[data-group-stem]' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', { 'data-group-stem': '', ...HTMLAttributes }, 0]
  },

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key,
        appendTransaction(trs, before, after) {
          // Undo and redo bring the count back with the questions: never recompute over them.
          if (!trs.some((t) => t.docChanged) || trs.some((t) => t.getMeta(OWN) || isHistoryTransaction(t)))
            return null
          const fixes = keepMembers(before.doc, after.doc)
          if (!fixes.length) return null
          const tr = after.tr
          for (const f of fixes) tr.setNodeMarkup(f.pos, undefined, { ...after.doc.nodeAt(f.pos)?.attrs, count: f.count })
          return tr.setMeta(OWN, true)
        },
        state: {
          init: (_c, state) => decorate(state.doc),
          apply: (tr, old) => (tr.docChanged ? decorate(tr.doc) : old),
        },
        props: {
          decorations: (state) => key.getState(state) as DecorationSet,
        },
      }),
    ]
  },

  addNodeView() {
    return ({ node, getPos, editor }: NodeViewRendererProps) => {
      let current = node
      const dom = document.createElement('div')
      dom.className = 'group-stem-block'
      dom.setAttribute('data-group-stem', '')
      dom.setAttribute('role', 'group')

      const head = document.createElement('div')
      head.className = 'group-head'
      head.setAttribute('contenteditable', 'false')
      const lead = document.createElement('p')
      lead.className = 'group-lead'
      const controls = document.createElement('div')
      controls.className = 'group-controls'
      const button = (cls: string, label: string, text: string, run: () => void) => {
        const b = document.createElement('button')
        b.type = 'button'
        b.className = `group-btn ${cls}`
        b.setAttribute('aria-label', label)
        b.title = label
        b.textContent = text
        b.addEventListener('mousedown', (e) => e.preventDefault()) // keep the editor's selection
        b.addEventListener('click', (e) => {
          e.preventDefault()
          run()
        })
        return b
      }
      const pos = () => {
        const p = getPos()
        return typeof p === 'number' ? p : null
      }
      const step = (delta: number) => {
        const p = pos()
        if (p === null) return
        const tr = setStemCount(editor.state, p, Number(current.attrs.count) + delta)
        if (tr) editor.view.dispatch(tr)
      }
      const fewer = button('group-fewer', 'Let the last question go from the stem', '−', () => step(-1))
      const more = button('group-more', 'Take in the next question', '+', () => step(1))
      const count = document.createElement('span')
      count.className = 'group-count'
      const remove = button('group-delete', 'Delete the shared stem (its questions stay)', 'Delete stem', () => {
        const p = pos()
        if (p === null) return
        editor.chain().focus().deleteRange({ from: p, to: p + current.nodeSize }).run()
      })
      controls.append(fewer, count, more, remove)
      head.append(lead, controls)

      const contentDOM = document.createElement('div')
      contentDOM.className = 'group-body'
      dom.append(head, contentDOM)

      const sync = () => {
        const p = pos()
        if (p === null) return
        let numbers: number[]
        let available = 0
        try {
          const { doc } = editor.state
          const at = doc.resolve(p).index(0)
          numbers = stemNumbers(doc, at, numberFrom(get(paperSettings)))
          // how many questions the stem could take in: up to the next section, page or stem
          const blocks = blocksOf(doc)
          for (let j = at + 1; j < blocks.length && !ENDS.includes(blocks[j].type); j++)
            if (QUESTIONS.includes(blocks[j].type)) available++
        } catch {
          return // the node view is being torn down
        }
        const sentence = stemSentence(numbers)
        lead.textContent = sentence || 'Shared stem: add the questions that use it below it.'
        lead.classList.toggle('empty', !sentence)
        const n = numbers.length
        count.textContent = `${n} question${n === 1 ? '' : 's'}`
        fewer.disabled = n <= 1
        more.disabled = n >= available || Number(current.attrs.count) >= MAX_GROUP_COUNT
        dom.setAttribute('aria-label', sentence ? `Shared stem for ${sentence.replace(/^Use the information below to answer /, '').replace(/\.$/, '')}` : 'Shared stem')
      }
      editor.on('transaction', sync)
      const stopSettings = paperSettings.subscribe(() => queueMicrotask(sync))
      queueMicrotask(sync)

      return {
        dom,
        contentDOM,
        update(next) {
          if (next.type !== current.type) return false
          current = next
          sync()
          return true
        },
        destroy() {
          editor.off('transaction', sync)
          stopSettings()
        },
        stopEvent: (event) => head.contains(event.target as globalThis.Node),
        ignoreMutation: (m) => !contentDOM.contains(m.target),
      }
    }
  },
})

/** Insert a stem before the question the caret is in, else after the block the caret is in; the
 *  caret goes into the stem. It covers the next two questions, or as many as there are before the
 *  next section, page or stem (at least one, so the next question added below joins it). */
export function insertStem(editor: NodeViewRendererProps['editor']) {
  const { state } = editor
  const { $from, from, to } = state.selection
  const top = $from.depth > 0 ? $from.before(1) : from
  const node = state.doc.nodeAt(top)
  const at = node && QUESTIONS.includes(node.type.name) ? top : $from.depth > 0 ? $from.after(1) : to
  let available = 0
  const index = state.doc.resolve(at).index(0)
  for (let i = index; i < state.doc.childCount; i++) {
    const name = state.doc.child(i).type.name
    if (ENDS.includes(name)) break
    if (QUESTIONS.includes(name)) available++
  }
  const count = Math.max(1, Math.min(2, available))
  const tr = state.tr.insert(at, state.schema.nodeFromJSON(stemNode(count)))
  tr.setSelection(TextSelection.create(tr.doc, at + 2)).scrollIntoView()
  editor.view.dispatch(tr)
  editor.view.focus()
}
