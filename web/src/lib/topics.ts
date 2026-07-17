// Single source of truth for the topic selector: display label → blueprint-code
// prefix. The blueprint code the engine expects is `${prefix}_${difficulty}`.
// Prefixes are verified against content/blueprints/*.yaml and the LADDERS keys
// in engine/exam_engine/ladder.py (the labels here mirror those ladder keys).

import type { Difficulty } from './types'

export interface Topic {
  /** Human-facing label, shown in the Topic dropdown. */
  label: string
  /** Blueprint-code prefix, e.g. `geometry_area` → `geometry_area_hard`. */
  prefix: string
}

export const TOPICS: readonly Topic[] = [
  { label: 'Ratio', prefix: 'ratio' },
  { label: 'Fractions', prefix: 'fractions' },
  { label: 'Percentage', prefix: 'percentage' },
  { label: 'Speed', prefix: 'speed' },
  { label: 'Geometry (Angles)', prefix: 'geometry_angle' },
  { label: 'Geometry (Area & Perimeter)', prefix: 'geometry_area' },
]

export const DIFFICULTIES: readonly Difficulty[] = ['easy', 'medium', 'hard']

/** Build the blueprint code the engine expects from a topic prefix + difficulty. */
export function blueprintCode(prefix: string, difficulty: Difficulty): string {
  return `${prefix}_${difficulty}`
}
