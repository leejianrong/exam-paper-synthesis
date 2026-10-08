// Shared test fixtures for the editor (not a test file).
import type { Question } from '../types'

export function makeQuestion(over: Partial<Question> = {}, text = 'Ann, Ben and Cal share $90 in the ratio 2 : 3 : 4.'): Question {
  return {
    id: 'ratio_medium:1',
    seed: 1,
    blueprint_code: 'ratio_medium',
    source_type: 'generated',
    parameters: { names: ['Ann', 'Ben', 'Cal'], ratio: [2, 3, 4], total: 90 },
    validation: { status: 'pass' },
    available_ops: ['regenerate', 'make-easier', 'make-harder', 'change-to-decimals', 'toggle-diagram'],
    question: {
      total_marks: 3,
      parts: [
        {
          text,
          marks: 3,
          answer: { type: 'quantity', value: 40, unit: '$' },
          solution_steps: [{ text: 'Total units = 2 + 3 + 4 = 9.' }, { text: 'Cal = 4 × $10 = $40.' }],
          marking_scheme: [{ type: 'M', mark: 1, description: 'Sum the units.' }],
          diagram: null,
        },
      ],
    },
    ...over,
  }
}

/** A sourced (bank) question: teacher-vouched, no blueprint, unreviewed by default. */
export function makeBankQuestion(over: Partial<Question> = {}): Question {
  return {
    id: 'sourced:rosyth-2023-q1',
    seed: 0,
    blueprint_code: '' as unknown as string,
    source_type: 'sourced',
    parameters: null,
    validation: { status: 'pass', checks: {} },
    question: {
      total_marks: 2,
      parts: [
        {
          text: 'Which shape has four equal sides and four right angles?',
          marks: 2,
          answer: { type: 'choice' },
          diagram: null,
        },
      ],
    },
    ...over,
  }
}

type Reply = unknown | ((init?: RequestInit) => unknown)

/**
 * A fetch stub that answers by URL suffix. Each reply is a JSON body (or a function of the
 * request init); an unmatched URL fails the test loudly so a missing stub is obvious.
 */
export function routeFetch(routes: Record<string, Reply>) {
  return async (url: string, init?: RequestInit) => {
    const key = Object.keys(routes).find((k) => String(url).includes(k))
    if (!key) throw new Error(`routeFetch: no stub for ${url}`)
    const reply = routes[key]
    const body = typeof reply === 'function' ? (reply as (i?: RequestInit) => unknown)(init) : reply
    const text = typeof body === 'string'
    return { ok: true, status: 200, json: async () => body, text: async () => (text ? body : JSON.stringify(body)) }
  }
}
