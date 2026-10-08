// The document model as the editor sees it: ProseMirror-style JSON (ADR-0021), kept
// deliberately loose — the server's document.schema.json is the authority.

import type { Question } from '../types'
import { assetUrl } from './assets'

export const DOCUMENT_SCHEMA_VERSION = '1.2.0'

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

export function totalMarks(doc: DocJSON): number {
  return numberedNodes(doc).reduce(
    (sum, n) =>
      sum +
      (n.type === 'freeformQuestion'
        ? ((n.attrs?.marks as number | null | undefined) ?? 0)
        : ((n.attrs?.question as Question | undefined)?.question?.total_marks ?? 0)),
    0,
  )
}

export const EMPTY_ANSWER: DocJSON = { type: 'doc', content: [] }

/** A free-form answer with trailing empty paragraphs dropped (empty ⇒ no content). */
export function normalizeAnswer(answer: DocJSON | undefined | null): DocJSON {
  const content = [...(answer?.content ?? [])]
  while (content.length) {
    const last = content[content.length - 1]
    if (last.type === 'paragraph' && !(last.content?.length)) content.pop()
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
const MARK_TAGS: Record<string, string> = { bold: 'strong', italic: 'em', underline: 'u' }

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
export function buildDocument(title: string, content: DocJSON): PaperDocument {
  const seen = new Set<string>()
  const blocks = (content.content ?? []).map((node) => {
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
  }
}
