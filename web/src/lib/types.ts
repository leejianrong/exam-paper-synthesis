// Pragmatic TypeScript view of the canonical question object — only the fields
// the SPA actually reads. The authoritative contract is the JSON Schema in
// schemas/canonical-question.schema.json; this mirror is deliberately loose
// (optional fields, a broad Answer) so the UI stays resilient to schema growth.

import type { EditOp } from './api'
import type { DiagramSpec } from './barModel'

export type ValidationStatus = 'pass' | 'fail'
export type Difficulty = 'easy' | 'medium' | 'hard'

/** A rendered answer. Fields present depend on `type`; kept broad on purpose. */
export interface Answer {
  type: string
  value?: number | string
  unit?: string
  numerator?: number
  denominator?: number
  parts?: Array<number | string>
  values?: Array<number | string>
  text?: string
}

export interface SolutionStep {
  text: string
}

export interface MarkingSchemeRow {
  /** Cambridge-style mark type: M (method), A (accuracy), or B (independent). */
  type: string
  mark: number
  description: string
}

export interface QuestionPart {
  text: string
  marks: number
  answer?: Answer
  solution_steps?: SolutionStep[]
  marking_scheme?: MarkingSchemeRow[]
  diagram?: DiagramSpec | null
}

/** The canonical question object, as consumed by the SPA. */
export interface Question {
  id: string
  seed: number
  blueprint_code: string
  parent_id?: string | null
  question: { parts: QuestionPart[]; total_marks: number }
  validation: { status: ValidationStatus }
  cognitive?: { difficulty?: Difficulty }
  /**
   * Engine-computed set of applicable edit ops (KAN-243), attached by the API as
   * a UI hint (not part of the canonical schema). Drives edit-button visibility;
   * the server is still the authoritative guard.
   */
  available_ops?: EditOp[]
}
