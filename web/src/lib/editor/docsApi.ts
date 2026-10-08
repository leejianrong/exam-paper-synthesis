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

export async function createDocument(title?: string): Promise<DocumentRecord> {
  const res = await apiFetch(`${BASE}/documents`, {
    method: 'POST',
    headers: json,
    body: JSON.stringify({ title: title ?? null }),
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
