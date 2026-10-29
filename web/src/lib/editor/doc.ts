// The document model as the editor sees it: ProseMirror-style JSON (ADR-0021), kept
// deliberately loose — the server's document.schema.json is the authority.

import type { Question } from '../types'
import { assetUrl } from './assets'
import type { PaperSettings } from './layout'

export const DOCUMENT_SCHEMA_VERSION = '1.6.0'

export interface DocNode {
  type: string
  attrs?: Record<string, unknown>
  content?: DocNode[]
  text?: string
  marks?: Array<{ type: string }>
}

export interface DocJSON {
  type: 'doc'
  content: DocNode[]
}

/** The stored document envelope (POST/PUT /documents). */
export interface PaperDocument {
  schema_version: string
  title: string
  content: DocJSON
  settings?: PaperSettings
}

export interface DocumentRecord {
  id: string
  title: string
  total_marks: number
  version: number
  created_at: string
  updated_at: string
  document: PaperDocument
}

export type DocumentSummary = Omit<DocumentRecord, 'document'>

/** A fresh stable block id (matches the server's ^[A-Za-z0-9_-]{4,64}$). */
export function newBlockId(): string {
  const bytes = new Uint8Array(8)
  crypto.getRandomValues(bytes)
  return 'b_' + Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')
}

/** The question nodes of a document, in order. */
export function questionNodes(doc: DocJSON): DocNode[] {
  return (doc.content ?? []).filter((n) => n.type === 'templatedQuestion')
}

export function questionsOf(doc: DocJSON): Question[] {
  return questionNodes(doc).map((n) => n.attrs?.question as Question)
}

/** Every numbered question block (templated and free-form), in document order. */
export function numberedNodes(doc: DocJSON): DocNode[] {
  return (doc.content ?? []).filter(
    (n) => n.type === 'templatedQuestion' || n.type === 'freeformQuestion',
  )
}

/** The lettered parts of a free-form question (P3), in order. */
export function freeformParts(node: DocNode): DocNode[] {
  return (node.content ?? []).filter((c) => c.type === 'freeformPart')
}

/** A free-form question's marks: the sum over its parts when it has any, else its own. */
export function freeformMarks(node: DocNode): number {
  const parts = freeformParts(node)
  if (parts.length) return parts.reduce((n, p) => n + ((p.attrs?.marks as number | null) ?? 0), 0)
  return (node.attrs?.marks as number | null | undefined) ?? 0
}

export function totalMarks(doc: DocJSON): number {
  return numberedNodes(doc).reduce(
    (sum, n) =>
      sum +
      (n.type === 'freeformQuestion'
        ? freeformMarks(n)
        : ((n.attrs?.question as Question | undefined)?.question?.total_marks ?? 0)),
    0,
  )
}

/** One block's marks (templated snapshot total, or a free-form question's own/parts). */
export function blockMarks(node: DocNode): number {
  return node.type === 'freeformQuestion'
    ? freeformMarks(node)
    : ((node.attrs?.question as Question | undefined)?.question?.total_marks ?? 0)
}

export type SectionMode = 'mcq' | 'short' | 'structured'

/** A section's figures: authored target, derived question range / count / marks (P4). */
export interface SectionInfo {
  first: number | null
  last: number | null
  count: number
  marks: number
  target: number | null
}

/**
 * The derived figures of every section, in order (mirror of the engine's `paper_outline`):
 * questions after a section divider belong to it until the next one; numbers continue.
 */
export function paperOutline(doc: DocJSON): SectionInfo[] {
  const out: SectionInfo[] = []
  let number = 0
  for (const n of doc.content ?? []) {
    if (n.type === 'section') {
      const t = n.attrs?.marks_target
      out.push({
        first: null,
        last: null,
        count: 0,
        marks: 0,
        target: typeof t === 'number' ? t : null,
      })
    } else if (n.type === 'templatedQuestion' || n.type === 'freeformQuestion') {
      number += 1
      const sec = out[out.length - 1]
      if (sec) {
        sec.first ??= number
        sec.last = number
        sec.count += 1
        sec.marks += blockMarks(n)
      }
    }
  }
  return out
}

export const EMPTY_ANSWER: DocJSON = { type: 'doc', content: [] }

/**
 * Strip editor-only attributes the document schema does not allow. TipTap's ordered list
 * carries a `type` (list-style) attribute — `null` by default — that must never reach the
 * server; `start` is kept only when it is not 1.
 */
export function cleanNode(node: DocNode): DocNode {
  let out = node
  if (node.type === 'orderedList') {
    const start = Number(node.attrs?.start)
    const rest: DocNode = { ...node }
    delete rest.attrs
    out = Number.isInteger(start) && start > 1 ? { ...rest, attrs: { start } } : rest
  }
  if (out.content) out = { ...out, content: out.content.map(cleanNode) }
  if ((out.type === 'templatedQuestion' || out.type === 'freeformQuestion') && out.attrs) {
    // The schema takes a remark only as a non-empty string; an unset or cleared one is absent.
    const { remark, ...rest } = out.attrs
    const text = typeof remark === 'string' ? remark.trim() : ''
    out = { ...out, attrs: text ? { ...rest, remark: text } : rest }
    // Layout overrides are optional: an unset one is absent (null/undefined), never a guess.
    const attrs = { ...(out.attrs as Record<string, unknown>) }
    if (attrs.space_mm === null || attrs.space_mm === undefined) delete attrs.space_mm
    if (attrs.ans_unit === null || attrs.ans_unit === undefined) delete attrs.ans_unit
    out = { ...out, attrs }
  }
  if (out.type === 'section' && out.attrs) {
    // Optional section fields are absent when unset; the title is always a string.
    const attrs: Record<string, unknown> = { title: String(out.attrs.title ?? '') }
    const instr = typeof out.attrs.instructions === 'string' ? out.attrs.instructions.trim() : ''
    if (instr) attrs.instructions = instr
    if (out.attrs.mode) attrs.mode = out.attrs.mode
    if (typeof out.attrs.marks_target === 'number') attrs.marks_target = out.attrs.marks_target
    out = { ...out, attrs }
  }
  if (out.type === 'freeformPart' && out.attrs) {
    const attrs = { ...(out.attrs as Record<string, unknown>) }
    if (attrs.space_mm === null || attrs.space_mm === undefined) delete attrs.space_mm
    if (attrs.ans_unit === null || attrs.ans_unit === undefined) delete attrs.ans_unit
    const answer = attrs.answer as DocJSON | undefined
    if (answer) attrs.answer = { ...answer, content: (answer.content ?? []).map(cleanNode) }
    out = { ...out, attrs }
  }
  if (out.type === 'freeformQuestion' && out.attrs?.answer) {
    const answer = out.attrs.answer as DocJSON
    out = {
      ...out,
      attrs: {
        ...out.attrs,
        answer: { ...answer, content: (answer.content ?? []).map(cleanNode) },
      },
    }
  }
  return out
}

/** A free-form answer with trailing empty paragraphs dropped (empty ⇒ no content). */
export function normalizeAnswer(answer: DocJSON | undefined | null): DocJSON {
  const content = (answer?.content ?? []).map(cleanNode)
  while (content.length) {
    const last = content[content.length - 1]
    if (last.type === 'paragraph' && !last.content?.length) content.pop()
    else break
  }
  return { type: 'doc', content }
}

/** A fresh, empty free-form question node (caret goes in its first paragraph). */
export function freeformNode(): DocNode {
  return {
    type: 'freeformQuestion',
    attrs: { block_id: newBlockId(), marks: null, answer: EMPTY_ANSWER },
    content: [{ type: 'paragraph' }],
  }
}

const esc = (t: string): string =>
  t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
const MARK_TAGS: Record<string, string> = {
  bold: 'strong',
  italic: 'em',
  underline: 'u',
}

/** Escaped HTML for a restricted text block list (read-only views of free-form text). */
export function blocksToHtml(nodes: DocNode[] | undefined): string {
  return (nodes ?? [])
    .map((n): string => {
      if (n.type === 'paragraph') return `<p>${inlineHtml(n.content)}</p>`
      if (n.type === 'bulletList' || n.type === 'orderedList') {
        const tag = n.type === 'bulletList' ? 'ul' : 'ol'
        return `<${tag}>${(n.content ?? []).map((li) => `<li>${blocksToHtml(li.content)}</li>`).join('')}</${tag}>`
      }
      if (n.type === 'image') {
        const a = n.attrs ?? {}
        const width = Number(a.width_pct) || 100
        return `<figure class="doc-image"><img src="${esc(assetUrl(String(a.asset_id)))}" alt="${esc(String(a.alt ?? ''))}" style="width:${width}%"></figure>`
      }
      return ''
    })
    .join('')
}

function inlineHtml(nodes: DocNode[] | undefined): string {
  return (nodes ?? [])
    .map((n) => {
      if (n.type === 'hardBreak') return '<br>'
      if (n.type === 'math') {
        const latex = String(n.attrs?.latex ?? '')
        return `<span class="math-host" data-latex="${esc(latex)}">${esc(latex)}</span>`
      }
      let html = esc(n.text ?? '')
      for (const m of n.marks ?? []) {
        const tag = MARK_TAGS[m.type]
        if (tag) html = `<${tag}>${html}</${tag}>`
      }
      return html
    })
    .join('')
}

/**
 * Wrap editor content in the stored envelope. Copy/paste can duplicate a question
 * block (and its block_id); the server rejects duplicates, so repeats get a fresh id.
 */
export function buildDocument(
  title: string,
  content: DocJSON,
  settings?: PaperSettings,
): PaperDocument {
  const seen = new Set<string>()
  const blocks = (content.content ?? []).map(cleanNode).map((node) => {
    if (node.type !== 'templatedQuestion' && node.type !== 'freeformQuestion') return node
    let id = String(node.attrs?.block_id ?? '')
    if (!id || seen.has(id)) id = newBlockId()
    seen.add(id)
    return { ...node, attrs: { ...node.attrs, block_id: id } }
  })
  return {
    schema_version: DOCUMENT_SCHEMA_VERSION,
    title,
    content: { type: 'doc', content: blocks },
    ...(settings && Object.keys(settings).length ? { settings } : {}),
  }
}
