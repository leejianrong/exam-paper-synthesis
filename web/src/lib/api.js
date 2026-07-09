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
