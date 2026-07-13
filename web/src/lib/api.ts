import type { Question } from './types'

const BASE: string = import.meta.env.VITE_API ?? 'http://localhost:8000'

/** The edit operations the API exposes at POST /edit/{op}. */
export type EditOp =
  | 'regenerate'
  | 'make-harder'
  | 'make-easier'
  | 'change-to-decimals'
  | 'toggle-diagram'

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
  const res = await fetch(`${BASE}/generate`, {
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
  const res = await fetch(`${BASE}/edit/${op}`, {
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
