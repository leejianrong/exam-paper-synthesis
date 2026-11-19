// What a question block offers (EXA-161): the pill's controls and the ⋯ menu's rows, as pure
// data from what kind of block it is. Rows that don't apply are left out, not greyed. The
// menu runs top to bottom: change it, keep it, place it, take it over, remove it.

import type { EditOp } from '../api'
import type { IconName } from '../Icon.svelte'
import { BLOCK_KEYS } from './shortcuts'

export type QuestionAction =
  | 'like' // another question for this slot (the server's `like` swap)
  | 'regenerate' // a new seed of the same blueprint, for a generated question no paper made
  | 'topic'
  | 'fill' // a placeholder: let the generator put a question here
  | 'easier'
  | 'harder'
  | 'names'
  | 'addPart'
  | 'lock'
  | 'key'
  | 'answer' // a teacher's own question: write its answer for the key (EXA-162)
  | 'up'
  | 'down'
  | 'addBelow'
  | 'own'
  | 'convert'
  | 'delete'
  | `op:${EditOp}` // the engine's other one-click edits, by available_ops

export interface QuestionFacts {
  /** generated: the engine wrote it (it can be swapped); bank: a templated question from the
   *  question bank; own: written by the teacher; placeholder: a generated paper's empty slot. */
  kind: 'generated' | 'bank' | 'own' | 'placeholder'
  locked: boolean
  /** "Regenerate unlocked" would refill it, so it can be locked. */
  lockable: boolean
  inKey: boolean
  /** The engine's one-click edits this question offers (templated only). */
  ops: EditOp[]
  /** Generated with cosmetic slots the engine can rename (not a multiple-choice copy). */
  canEditNames: boolean
  /** A free-form question with room for another lettered part. */
  canAddPart: boolean
  canMoveUp: boolean
  canMoveDown: boolean
  /** How the op-specific rows read (they depend on the question's diagram). */
  opLabels?: Partial<Record<EditOp, string>>
}

export interface QuestionRow {
  action: QuestionAction
  label: string
  icon?: IconName
  shortcut?: string
  hint?: string
  danger?: boolean
}

const OP_DEFAULT: Partial<Record<EditOp, string>> = {
  'change-to-decimals': 'Change to decimals',
  'toggle-diagram': 'Show model in key',
  'toggle-bar-view': 'Slice into units',
}

/** The menu's rows in groups (a separator between groups; empty groups dropped). */
export function menuGroups(f: QuestionFacts): QuestionRow[][] {
  const change: QuestionRow[] = []
  if (f.kind === 'generated' && !f.locked) {
    change.push(
      { action: 'like', label: 'Another like this', icon: 'swap', shortcut: BLOCK_KEYS.like, hint: 'Another question for this place: same marks, same topic where possible' },
      { action: 'topic', label: 'Another topic', icon: 'topic', hint: 'A question with the same marks from a topic this paper uses less' },
    )
  } else if (f.kind !== 'generated' && f.kind !== 'placeholder' && f.ops.includes('regenerate')) {
    // Reachable: the API gives `available_ops` (regenerate among them) to any templated question
    // that names a blueprint (`ops.with_document_hints`), and a bank copy may still name one.
    change.push({ action: 'regenerate', label: 'Another like this', icon: 'swap', shortcut: BLOCK_KEYS.like, hint: 'The same kind of question with new numbers' })
  }
  if (f.kind === 'placeholder' && !f.locked) {
    change.push(
      { action: 'fill', label: 'Fill with a question', icon: 'swap', shortcut: BLOCK_KEYS.like, hint: 'Let the generator put a question with these marks here' },
      { action: 'topic', label: 'Another topic', icon: 'topic', hint: 'Fill it with a question from a topic this paper uses less' },
    )
  }
  if (f.ops.includes('make-easier')) change.push({ action: 'easier', label: 'Make easier', icon: 'easier', shortcut: BLOCK_KEYS.easier })
  if (f.ops.includes('make-harder')) change.push({ action: 'harder', label: 'Make harder', icon: 'harder', shortcut: BLOCK_KEYS.harder })
  if (f.canEditNames) change.push({ action: 'names', label: 'Edit names…', icon: 'names' })
  for (const op of ['change-to-decimals', 'toggle-diagram', 'toggle-bar-view'] as EditOp[]) {
    if (f.ops.includes(op)) change.push({ action: `op:${op}`, label: f.opLabels?.[op] ?? OP_DEFAULT[op] ?? op })
  }
  if (f.canAddPart) change.push({ action: 'addPart', label: 'Add a part', icon: 'part', hint: 'Add a lettered part, (a), (b), …' })

  const keep: QuestionRow[] = []
  if (f.lockable) {
    keep.push(
      f.locked
        ? { action: 'lock', label: 'Unlock', icon: 'unlock', shortcut: BLOCK_KEYS.lock }
        : { action: 'lock', label: 'Lock', icon: 'lock', shortcut: BLOCK_KEYS.lock, hint: 'Keep this question when you regenerate the paper' },
    )
  }
  if (f.kind === 'own') keep.push({ action: 'answer', label: 'Edit answer…', icon: 'pen', hint: 'Write the answer that prints in the answer key' })
  keep.push({ action: 'key', label: f.inKey ? 'Leave out of answer key' : 'Include in answer key', icon: 'key' })

  const place: QuestionRow[] = []
  if (f.canMoveUp) place.push({ action: 'up', label: 'Move up', icon: 'harder', shortcut: BLOCK_KEYS.up })
  if (f.canMoveDown) place.push({ action: 'down', label: 'Move down', icon: 'easier', shortcut: BLOCK_KEYS.down })
  place.push({ action: 'addBelow', label: 'Add question below', icon: 'plus' })

  const takeOver: QuestionRow[] = []
  if (f.kind === 'generated' && !f.locked) {
    takeOver.push({ action: 'own', label: 'Replace with my own question', icon: 'pen', hint: 'Empty this place, keeping its marks, for a question you write' })
  }
  if (f.kind === 'generated' || f.kind === 'bank') {
    takeOver.push({ action: 'convert', label: 'Edit as my own text…', icon: 'text', hint: 'Turn it into text you can edit; the engine stops checking it' })
  }

  const remove: QuestionRow[] = [{ action: 'delete', label: 'Delete', icon: 'trash', shortcut: BLOCK_KEYS.delete, danger: true }]
  return [change, keep, place, takeOver, remove].filter((g) => g.length > 0)
}

/** The pill's first controls (before ⋯): the one action a teacher reaches for most. */
export function pillActions(f: QuestionFacts): Array<'primary' | 'addPart' | 'lock'> {
  const out: Array<'primary' | 'addPart' | 'lock'> = []
  if (f.kind === 'placeholder') {
    // a structured slot is written as lettered parts, so "+ Part" stays on a placeholder
    if (!f.locked) out.push('primary')
    if (f.canAddPart) out.push('addPart')
    return out
  }
  if (f.kind === 'own') {
    if (f.canAddPart) out.push('addPart')
  } else if (primaryRow(f)) {
    out.push('primary')
  }
  if (f.lockable) out.push('lock')
  return out
}

/** The pill's labelled button: "Another like this" (or "Fill with a question"). */
export function primaryRow(f: QuestionFacts): QuestionRow | undefined {
  const first = menuGroups(f)[0]?.[0]
  return first && ['like', 'regenerate', 'fill'].includes(first.action) ? first : undefined
}

/** The row a shortcut stands for, if the menu shows it. */
export function rowForShortcut(f: QuestionFacts, key: string): QuestionRow | undefined {
  return menuGroups(f)
    .flat()
    .find((r) => r.shortcut === key)
}

/** "Question 6, 2 marks, locked": the block's accessible name. */
export function blockLabel(n: number | null, marks: number | null, f: Pick<QuestionFacts, 'locked' | 'kind'>): string {
  const parts = [n === null ? 'Question' : `Question ${n}`]
  if (marks !== null) parts.push(`${marks} mark${marks === 1 ? '' : 's'}`)
  if (f.kind === 'placeholder') parts.push('to write')
  if (f.locked) parts.push('locked')
  return parts.join(', ')
}
