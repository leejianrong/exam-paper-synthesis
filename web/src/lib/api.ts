import { apiFetch } from './http'
import type { Question } from './types'

const BASE: string = import.meta.env.VITE_API ?? 'http://localhost:8000'

/** The edit operations the API exposes at POST /edit/{op}. */
export type EditOp =
  | 'regenerate'
  | 'make-harder'
  | 'make-easier'
  | 'change-to-decimals'
  | 'toggle-diagram'
  | 'toggle-bar-view'

interface GenerateResponse {
  questions: Question[]
}

interface EditResponse {
  question: Question
}

/**
 * Generate questions from a blueprint. Returns an array of canonical objects.
 */
export async function generate(blueprintCode: string, count = 1): Promise<Question[]> {
  const res = await apiFetch(`${BASE}/generate`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ blueprint_code: blueprintCode, count }),
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`API ${res.status}: ${detail}`)
  }
  const data = (await res.json()) as GenerateResponse
  return data.questions
}

/**
 * Apply one edit operation to a question. Returns the child canonical object.
 * `seed` optionally pins deterministic resample ops; child.parent_id links back.
 */
export async function editQuestion(
  op: EditOp,
  question: Question,
  seed: number | null = null,
): Promise<Question> {
  const res = await apiFetch(`${BASE}/edit/${op}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ question, seed }),
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`API ${res.status}: ${detail}`)
  }
  const data = (await res.json()) as EditResponse
  return data.question
}

/** The two PDF export flavours the API exposes at POST /export/{kind}. */
export type ExportKind = 'worksheet' | 'answer-key'

/**
 * Render the approved worksheet to a self-contained HTML document for preview
 * (POST /export/preview). Returns the HTML string (text/html) so the caller can
 * open it in a new tab — the document's inlined KaTeX bootstrap makes the
 * preview the exact print doc.
 */
export async function previewWorksheet(title: string, questions: Question[]): Promise<string> {
  const res = await apiFetch(`${BASE}/export/preview`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ title, questions }),
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`API ${res.status}: ${detail}`)
  }
  return res.text()
}

/**
 * Export the approved set as a PDF (POST /export/worksheet or
 * /export/answer-key). Returns the PDF as a Blob for a browser download.
 */
export async function exportPdf(
  kind: ExportKind,
  title: string,
  questions: Question[],
): Promise<Blob> {
  const res = await apiFetch(`${BASE}/export/${kind}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ title, questions }),
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`API ${res.status}: ${detail}`)
  }
  return res.blob()
}

/** One cosmetic (name/item) slot of a blueprint, from GET /blueprints/{code}/params (W1a). */
export interface EditableSlot {
  key: string
  role: 'name' | 'item'
  /** Number of values: 1 for a scalar, the array length for a list of names. */
  count: number
  max_length?: number
  /** Allowed values for an `item` slot (a fixed list — no free text). */
  pool?: string[]
}

/** The cosmetic slots of a blueprint, for building the "Edit names" form. */
export async function getEditableSlots(blueprintCode: string): Promise<EditableSlot[]> {
  const res = await apiFetch(`${BASE}/blueprints/${blueprintCode}/params`)
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`API ${res.status}: ${detail}`)
  }
  const data = (await res.json()) as { slots: EditableSlot[] }
  return data.slots
}

/**
 * Rename people / swap an item without touching the maths (POST /edit/set-cosmetic).
 * `changes` maps a parameter to its new value(s), e.g. `{ names: ['Ann', 'Ben'] }`.
 */
export async function setCosmetic(
  question: Question,
  changes: Record<string, string | string[]>,
): Promise<Question> {
  const res = await apiFetch(`${BASE}/edit/set-cosmetic`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ question, changes }),
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`API ${res.status}: ${detail}`)
  }
  const data = (await res.json()) as EditResponse
  return data.question
}

/** One question in the owner's bank (GET /bank). */
export interface BankItem {
  id: string
  topic: string | null
  level: string | null
  difficulty: string | null
  source_type: string
  reviewed: boolean
  question: Question
}

/** The owner's bank questions (import: `importBank` here, or `mathgen bank import`). */
export async function listBank(): Promise<BankItem[]> {
  const res = await apiFetch(`${BASE}/bank`)
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`API ${res.status}: ${detail}`)
  }
  return ((await res.json()) as { items: BankItem[] }).items
}

/**
 * Mark a bank question reviewed (or withdraw that): ADR-0019's deliberate human act. Resolves
 * `false` when the question is no longer in the owner's bank (404), so a paper's own copy can
 * still be reviewed; any other failure throws.
 */
export async function setBankReviewed(id: string, reviewed: boolean): Promise<boolean> {
  const res = await apiFetch(`${BASE}/bank/${encodeURIComponent(id)}/review`, {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ reviewed }),
  })
  if (res.status === 404) return false
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`API ${res.status}: ${detail}`)
  }
  return true
}

/** One item's outcome from POST /bank/import. */
export interface ImportResult {
  index: number
  id: string | null
  status: 'imported' | 'replaced' | 'duplicate' | 'invalid'
  errors?: string[]
}

export interface ImportResponse {
  results: ImportResult[]
  imported: number
  replaced: number
  duplicate: number
  invalid: number
}

/**
 * Import canonical objects into the owner's bank (POST /bank/import). Items arrive
 * unreviewed; a duplicate id is reported unless `replace`; one bad item never blocks the rest.
 */
export async function importBank(objects: unknown[], replace = false): Promise<ImportResponse> {
  const res = await apiFetch(`${BASE}/bank/import`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ objects, replace }),
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = (await res.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      /* keep statusText */
    }
    throw new Error(`Import failed: ${detail}`)
  }
  return (await res.json()) as ImportResponse
}

/** A question converted to free-form pieces (POST /convert/freeform). */
export interface FreeformConversion {
  marks: number
  content: Array<Record<string, unknown>>
  answer: { type: 'doc'; content: Array<Record<string, unknown>> }
  /** Figures that could not be drawn, by name (the conversion still succeeded). */
  dropped: string[]
}

export async function convertToFreeform(question: Question): Promise<FreeformConversion> {
  const res = await apiFetch(`${BASE}/convert/freeform`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`API ${res.status}: ${detail}`)
  }
  return (await res.json()) as FreeformConversion
}

/** Engine-rendered HTML for one question (POST /render/question): the print markup. */
export async function renderQuestionHtml(
  question: Question,
  mode: 'student' | 'key' = 'student',
  number: number | null = null,
): Promise<string> {
  const res = await apiFetch(`${BASE}/render/question`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ question, mode, number }),
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`API ${res.status}: ${detail}`)
  }
  return ((await res.json()) as { html: string }).html
}

/** The shared stylesheet / script for embedded engine fragments. */
export async function fetchFragmentAssets(): Promise<{ css: string; js: string }> {
  const [css, js] = await Promise.all([
    apiFetch(`${BASE}/render/question.css`),
    apiFetch(`${BASE}/render/katex.js`),
  ])
  if (!css.ok || !js.ok) throw new Error(`API ${css.ok ? js.status : css.status}: render assets`)
  return { css: await css.text(), js: await js.text() }
}

/** The engine's inline SVG for one diagram (POST /render/diagram). */
export async function renderDiagramSvg(diagram: unknown): Promise<string> {
  const res = await apiFetch(`${BASE}/render/diagram`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ diagram }),
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`API ${res.status}: ${detail}`)
  }
  return ((await res.json()) as { svg: string }).svg
}
