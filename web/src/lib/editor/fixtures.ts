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
