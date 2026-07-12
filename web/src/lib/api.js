const BASE = import.meta.env.VITE_API ?? 'http://localhost:8000'

/**
 * Generate questions from a blueprint. Returns an array of canonical objects.
 * @param {string} blueprintCode
 * @param {number} count
 */
export async function generate(blueprintCode, count = 1) {
  const res = await fetch(`${BASE}/generate`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ blueprint_code: blueprintCode, count }),
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`API ${res.status}: ${detail}`)
  }
  const data = await res.json()
  return data.questions
}

/**
 * Apply one edit operation to a question. Returns the child canonical object.
 * @param {string} op  one of: regenerate, make-harder, make-easier,
 *                      change-to-decimals, toggle-diagram
 * @param {object} question  the source canonical object
 * @param {number|null} seed  optional seed for deterministic resample ops
 */
export async function editQuestion(op, question, seed = null) {
  const res = await fetch(`${BASE}/edit/${op}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ question, seed }),
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`API ${res.status}: ${detail}`)
  }
  const data = await res.json()
  return data.question
}
