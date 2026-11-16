// Client for the tenant-scoped /documents API (W1b). Identity is the server's concern
// (dev stub today, session cookie in W3), so nothing identity-related is sent here.

import { apiFetch } from '../http'
import type { DocumentRecord, DocumentSummary, PaperDocument } from './doc'

const BASE: string = import.meta.env.VITE_API ?? 'http://localhost:8000'

export type ExportMode = 'student' | 'key' | 'full'

export class ApiError extends Error {
  status: number
  detail: unknown
  constructor(status: number, detail: unknown) {
    super(`API ${status}: ${typeof detail === 'string' ? detail : JSON.stringify(detail)}`)
    this.status = status
    this.detail = detail
  }
}

async function fail(res: Response): Promise<never> {
  let detail: unknown
  try {
    const body = (await res.json()) as { detail?: unknown }
    detail = body.detail ?? body
  } catch {
    detail = res.statusText
  }
  throw new ApiError(res.status, detail)
}

const json = { 'content-type': 'application/json' }

export async function listDocuments(): Promise<DocumentSummary[]> {
  const res = await apiFetch(`${BASE}/documents`)
  if (!res.ok) return fail(res)
  return ((await res.json()) as { documents: DocumentSummary[] }).documents
}

export async function createDocument(title?: string, template?: string): Promise<DocumentRecord> {
  const res = await apiFetch(`${BASE}/documents`, {
    method: 'POST',
    headers: json,
    body: JSON.stringify({ title: title ?? null, template: template ?? null }),
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

export async function exportDocument(id: string, mode: ExportMode): Promise<Blob> {
  const res = await apiFetch(`${BASE}/documents/${id}/export/${mode}`, { method: 'POST' })
  if (res.status === 429) {
    // The account's export allowance: the server's message already says when to retry.
    const body = (await res.json().catch(() => ({}))) as { detail?: unknown }
    throw new Error(typeof body.detail === 'string' ? body.detail : 'Export limit reached. Try again later.')
  }
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
): Promise<DocumentRecord & { report: PaperReport }> {
  const res = await apiFetch(`${BASE}/documents/generate`, {
    method: 'POST',
    headers: json,
    body: JSON.stringify({ template, level }),
  })
  if (!res.ok) return fail(res)
  return (await res.json()) as DocumentRecord & { report: PaperReport }
}

/** P8d: how to replace one question of a paper. */
export type SwapMode = 'like' | 'topic' | 'own'

/** What a swap did (engine `paper_swap.swap_question`'s report). */
export interface SwapReport {
  block_id: string
  mode: SwapMode
  marks: number
  placeholder: boolean
  blueprint?: string
  topic?: string
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
): Promise<DocumentRecord & { report: SwapReport }> {
  const res = await apiFetch(`${BASE}/documents/${id}/swap`, {
    method: 'POST',
    headers: json,
    body: JSON.stringify({ block_id: blockId, mode, base_version: baseVersion }),
  })
  if (!res.ok) return fail(res)
  return (await res.json()) as DocumentRecord & { report: SwapReport }
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
