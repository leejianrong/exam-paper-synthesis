// Client for the tenant-scoped /documents API (W1b). Identity is the server's concern
// (dev stub today, session cookie in W3), so nothing identity-related is sent here.

import { ApiError, fail } from '../errors'
import { apiFetch } from '../http'
import type { BankItem } from '../api'
import type { DocumentRecord, DocumentSummary, PaperDocument } from './doc'

const BASE: string = import.meta.env.VITE_API ?? 'http://localhost:8000'

export type ExportMode = 'student' | 'key' | 'full'

const json = { 'content-type': 'application/json' }

export async function listDocuments(): Promise<DocumentSummary[]> {
  const res = await apiFetch(`${BASE}/documents`)
  if (!res.ok) return fail(res)
  return ((await res.json()) as { documents: DocumentSummary[] }).documents
}

export async function createDocument(
  title?: string,
  template?: string,
  folderId?: string | null,
): Promise<DocumentRecord> {
  const res = await apiFetch(`${BASE}/documents`, {
    method: 'POST',
    headers: json,
    body: JSON.stringify({ title: title ?? null, template: template ?? null, folder_id: folderId ?? null }),
  })
  if (!res.ok) return fail(res)
  return (await res.json()) as DocumentRecord
}

export async function getDocument(id: string): Promise<DocumentRecord> {
  const res = await apiFetch(`${BASE}/documents/${id}`)
  if (!res.ok) return fail(res)
  return (await res.json()) as DocumentRecord
}

export async function saveDocument(
  id: string,
  document: PaperDocument,
  baseVersion: number,
): Promise<DocumentRecord> {
  const res = await apiFetch(`${BASE}/documents/${id}`, {
    method: 'PUT',
    headers: json,
    body: JSON.stringify({ document, base_version: baseVersion }),
  })
  if (!res.ok) return fail(res)
  return (await res.json()) as DocumentRecord
}

export async function deleteDocument(id: string): Promise<void> {
  const res = await apiFetch(`${BASE}/documents/${id}`, { method: 'DELETE' })
  if (!res.ok) return fail(res)
}

/** The true-print HTML for a document (same renderer the PDF is made from). */
export async function previewDocument(id: string, mode: ExportMode): Promise<string> {
  const res = await apiFetch(`${BASE}/documents/${id}/preview/${mode}`)
  if (!res.ok) return fail(res)
  return res.text()
}

/** The API's 409 when a paper still has empty generator placeholders (EXA-137). */
export interface UnfilledPlaceholders {
  code: 'unfilled_placeholders'
  message: string
  questions: number[]
}

export function unfilledDetail(e: unknown): UnfilledPlaceholders | null {
  if (!(e instanceof ApiError) || e.status !== 409) return null
  const d = e.detail as Partial<UnfilledPlaceholders> | null
  return d && d.code === 'unfilled_placeholders' && Array.isArray(d.questions)
    ? (d as UnfilledPlaceholders)
    : null
}

/** The paper as a PDF. A paper with empty placeholders is refused (`unfilledDetail`) unless
 *  `allowPlaceholders` says to print it anyway. */
export async function exportDocument(id: string, mode: ExportMode, allowPlaceholders = false): Promise<Blob> {
  const query = allowPlaceholders ? '?allow_placeholders=true' : ''
  const res = await apiFetch(`${BASE}/documents/${id}/export/${mode}${query}`, { method: 'POST' })
  if (!res.ok) return fail(res)
  return res.blob()
}

/** A paper template (P8a, engine content): the starter buttons and the generate dialog. */
export interface PaperTemplateInfo {
  code: string
  label: string
  title: string
  time_min: number
  sections: { title: string; mode: string; marks_target: number; questions: number }[]
}

export async function listPaperTemplates(): Promise<{ templates: PaperTemplateInfo[]; levels: string[] }> {
  const res = await apiFetch(`${BASE}/papers`)
  if (!res.ok) return fail(res)
  return (await res.json()) as { templates: PaperTemplateInfo[]; levels: string[] }
}

/** What the generator filled, per section (engine `paper.generate_paper`'s report). */
export interface PaperReport {
  template: string
  level: string
  seed: number
  title: string
  filled: number
  placeholders: number
  placeholder_marks: number
  sections: {
    title: string
    mode: string
    marks_target: number
    slots: number
    filled: number
    /** P8c: real multi-part questions in a structured section (absent on older reports). */
    multipart?: number
    stand_ins: number
    placeholders: number
    placeholder_marks: number
  }[]
  topics: Record<string, number>
}

export async function generatePaper(
  template: string,
  level: string,
  folderId?: string | null,
  /** EXA-153: for one paper of an exam set, the topics of the set's papers made so far. */
  setTopics?: Record<string, number>,
): Promise<DocumentRecord & { report: PaperReport }> {
  const res = await apiFetch(`${BASE}/documents/generate`, {
    method: 'POST',
    headers: json,
    body: JSON.stringify({
      template,
      level,
      folder_id: folderId ?? null,
      ...(setTopics ? { set_topics: setTopics } : {}),
    }),
  })
  if (!res.ok) return fail(res)
  return (await res.json()) as DocumentRecord & { report: PaperReport }
}

/** P8d: how to replace one question of a paper; `bank` (EXA-33) puts a question from the
 *  owner's bank there, picked from `bankSwapOptions`. */
export type SwapMode = 'like' | 'topic' | 'own' | 'bank'

/** What a swap did (engine `paper_swap.swap_question`'s report). */
export interface SwapReport {
  block_id: string
  mode: SwapMode
  marks: number
  placeholder: boolean
  blueprint?: string
  topic?: string
  bank_id?: string
  /** A generated question from the bank is locked, so regenerating keeps it (EXA-33). */
  locked?: boolean
}

/** What "regenerate unlocked" did (engine `paper_swap.regenerate_unlocked`'s report). */
export interface RegenerateReport {
  replaced: number
  placeholders: number
  kept: number
}

/** Swap one question on the server, computed on `baseVersion` (409 if the paper moved on). */
export async function swapQuestion(
  id: string,
  blockId: string,
  mode: SwapMode,
  baseVersion: number,
  bankId?: string,
): Promise<DocumentRecord & { report: SwapReport }> {
  const res = await apiFetch(`${BASE}/documents/${id}/swap`, {
    method: 'POST',
    headers: json,
    body: JSON.stringify({ block_id: blockId, mode, base_version: baseVersion, ...(bankId ? { bank_id: bankId } : {}) }),
  })
  if (!res.ok) return fail(res)
  return (await res.json()) as DocumentRecord & { report: SwapReport }
}

/** EXA-33: the owner's bank questions that could take this question's place, best first. */
export async function bankSwapOptions(id: string, blockId: string): Promise<BankItem[]> {
  const res = await apiFetch(`${BASE}/documents/${id}/swap/bank?block_id=${encodeURIComponent(blockId)}`)
  if (!res.ok) return fail(res)
  return ((await res.json()) as { items: BankItem[] }).items
}

/** Refill every unlocked generated question and empty placeholder (locked ones stay). */
export async function regeneratePaper(
  id: string,
  baseVersion: number,
): Promise<DocumentRecord & { report: RegenerateReport }> {
  const res = await apiFetch(`${BASE}/documents/${id}/regenerate`, {
    method: 'POST',
    headers: json,
    body: JSON.stringify({ base_version: baseVersion }),
  })
  if (!res.ok) return fail(res)
  return (await res.json()) as DocumentRecord & { report: RegenerateReport }
}

/** O2: a folder of papers (owner-scoped). `papers` is the server's count when listed. */
export interface Folder {
  id: string
  name: string
  created_at: string
  updated_at: string
  papers?: number
}

export async function listFolders(): Promise<Folder[]> {
  const res = await apiFetch(`${BASE}/folders`)
  if (!res.ok) return fail(res)
  return ((await res.json()) as { folders: Folder[] }).folders
}

export async function createFolder(name: string): Promise<Folder> {
  const res = await apiFetch(`${BASE}/folders`, { method: 'POST', headers: json, body: JSON.stringify({ name }) })
  if (!res.ok) return fail(res)
  return (await res.json()) as Folder
}

export async function renameFolder(id: string, name: string): Promise<Folder> {
  const res = await apiFetch(`${BASE}/folders/${id}`, { method: 'PATCH', headers: json, body: JSON.stringify({ name }) })
  if (!res.ok) return fail(res)
  return (await res.json()) as Folder
}

/** Delete a folder: its papers become unfiled on the server, never deleted. */
export async function deleteFolder(id: string): Promise<void> {
  const res = await apiFetch(`${BASE}/folders/${id}`, { method: 'DELETE' })
  if (!res.ok) return fail(res)
}

/** File a paper in a folder, or `null` to unfile it. Not an edit: the version stays. */
export async function moveDocument(id: string, folderId: string | null): Promise<DocumentSummary> {
  const res = await apiFetch(`${BASE}/documents/${id}`, {
    method: 'PATCH',
    headers: json,
    body: JSON.stringify({ folder_id: folderId }),
  })
  if (!res.ok) return fail(res)
  return (await res.json()) as DocumentSummary
}

/** Rename a paper from the list (EXA-166): its title is part of the content, so this is a save. */
export async function renameDocument(id: string, title: string): Promise<DocumentRecord> {
  const rec = await getDocument(id)
  return saveDocument(id, { ...rec.document, title }, rec.version)
}

/** The schema's longest title (document.schema.json `title.maxLength`), in code points. */
export const TITLE_MAX = 200

/** "Copy of …", cut to the longest title the schema allows. */
export function copyTitle(title: string): string {
  return [...`Copy of ${title || 'Untitled paper'}`].slice(0, TITLE_MAX).join('')
}

/**
 * Make a copy (EXA-166): "Copy of …" in the same folder with the same content and settings. There
 * is no copy endpoint, so it is a create and a save; a copy left empty by a failed save is
 * deleted again. The list copies the saved paper; the editor passes what it holds (`from`).
 */
export async function copyDocument(
  id: string,
  from?: { document: PaperDocument; folder_id: string | null },
): Promise<DocumentRecord> {
  const src = from ?? (await getDocument(id))
  const title = copyTitle(src.document.title)
  const made = await createDocument(title, undefined, src.folder_id ?? null)
  try {
    return await saveDocument(made.id, { ...src.document, title }, made.version)
  } catch (e) {
    await deleteDocument(made.id).catch(() => {})
    throw e
  }
}
