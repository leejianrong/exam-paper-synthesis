// Shared test fixtures for the editor (not a test file).
import type { Question } from '../types'

/** A generated multi-part question (P8c): a shared stem and parts (a) and (b). */
export function makeMultipartQuestion(): Question {
  const part = (label: string, text: string, marks: number, value: number) => ({
    label,
    text,
    marks,
    answer: { type: 'quantity', value, unit: 'km' },
    solution_steps: [{ text: `Work for (${label}).` }],
    marking_scheme: [{ type: 'A', mark: marks, description: 'Correct.' }],
    diagram: null,
  })
  return makeQuestion({
    id: 'speed_structured:1',
    blueprint_code: 'speed_structured',
    available_ops: ['regenerate'],
    question: {
      stem: 'Ben drove from Town P to Town Q.',
      total_marks: 4,
      parts: [part('a', 'Find the distance.', 1, 120), part('b', 'Find the average speed.', 3, 48)],
    },
  } as Partial<Question>)
}

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

/** Wrap questions as document nodes, as the page hands them to the answer key. */
export function templatedNodes(questions: Question[]) {
  return questions.map((question, i) => ({
    type: 'templatedQuestion',
    attrs: { block_id: `blk_${i}`, question },
  }))
}

export function freeformDocNode(over: { id?: string; marks?: number | null; body?: string; answer?: string } = {}) {
  const para = (t: string) => ({ type: 'paragraph', content: [{ type: 'text', text: t }] })
  return {
    type: 'freeformQuestion',
    attrs: {
      block_id: over.id ?? 'ff_test_1',
      marks: over.marks === undefined ? 3 : over.marks,
      answer: { type: 'doc', content: over.answer ? [para(over.answer)] : [] },
    },
    content: [para(over.body ?? 'How many sweets are left?')],
  }
}

/** A generated single-part question that prints a data table (EXA-148, postage_table). */
export function makeTableQuestion(over: Partial<Question> = {}): Question {
  const base = makeQuestion(
    { id: 'postage_table:1', blueprint_code: 'postage_table' },
    'Ben posted two letters. One letter had a mass of 35 g and the other had a mass of 120 g.',
  )
  return {
    ...base,
    question: {
      ...base.question,
      stem: 'The table shows the postage for sending a letter.',
      table: {
        caption: 'Postage for letters',
        headers: ['Mass of letter', 'Postage'],
        rows: [
          ['Up to 20 g', '$0.40'],
          ['Above 20 g, up to 40 g', '$0.55'],
        ],
      },
    },
    ...over,
  }
}
