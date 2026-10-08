// The document model as the editor sees it: ProseMirror-style JSON (ADR-0021), kept
// deliberately loose — the server's document.schema.json is the authority.

import type { Question } from '../types'

export const DOCUMENT_SCHEMA_VERSION = '1.0.0'

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

export function totalMarks(doc: DocJSON): number {
  return questionsOf(doc).reduce((sum, q) => sum + (q?.question?.total_marks ?? 0), 0)
}

/**
 * Wrap editor content in the stored envelope. Copy/paste can duplicate a question
 * block (and its block_id); the server rejects duplicates, so repeats get a fresh id.
 */
export function buildDocument(title: string, content: DocJSON): PaperDocument {
  const seen = new Set<string>()
  const blocks = (content.content ?? []).map((node) => {
    if (node.type !== 'templatedQuestion') return node
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
