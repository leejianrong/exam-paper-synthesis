// The question bank page's filters (EXA-167): pure, so the page only wires them up. Options come
// from what is in the bank, so a filter never offers a value that would match nothing.

import type { BankItem } from './api'
import { titleMatches } from './editor/folders'

export type ReviewFilter = '' | 'reviewed' | 'unreviewed'

export interface BankFilters {
  query: string
  topic: string
  level: string
  difficulty: string
  source: string
  review: ReviewFilter
}

export const NO_FILTERS: BankFilters = { query: '', topic: '', level: '', difficulty: '', source: '', review: '' }

export const SOURCE_LABELS: Record<string, string> = { sourced: 'Imported', generated: 'Generated' }

const DIFFICULTY_ORDER = ['easy', 'medium', 'hard']

/** Only imported questions are reviewed (ADR-0019); a generated one is proven by the engine. */
export const needsReview = (item: BankItem): boolean => item.source_type === 'sourced'

const distinct = (values: Array<string | null>): string[] =>
  [...new Set(values.filter((v): v is string => !!v))].sort()

export function filterOptions(items: BankItem[]) {
  return {
    topics: distinct(items.map((i) => i.topic)),
    levels: distinct(items.map((i) => i.level)),
    difficulties: distinct(items.map((i) => i.difficulty)).sort(
      (a, b) => DIFFICULTY_ORDER.indexOf(a) - DIFFICULTY_ORDER.indexOf(b),
    ),
    sources: distinct(items.map((i) => i.source_type)),
  }
}

/** The words a search looks through: the question's text, its topic and its id. */
export function searchText(item: BankItem): string {
  const q = item.question.question
  return [item.id, item.topic, q.stem, ...q.parts.map((p) => p.text)].filter(Boolean).join(' ')
}

export function filterBank(items: BankItem[], f: BankFilters): BankItem[] {
  return items.filter(
    (i) =>
      (!f.topic || i.topic === f.topic) &&
      (!f.level || i.level === f.level) &&
      (!f.difficulty || i.difficulty === f.difficulty) &&
      (!f.source || i.source_type === f.source) &&
      (!f.review || (f.review === 'reviewed' ? i.reviewed : needsReview(i) && !i.reviewed)) &&
      (!f.query.trim() || titleMatches(searchText(i), f.query)),
  )
}

export const isFiltered = (f: BankFilters): boolean =>
  Object.entries(f).some(([k, v]) => (k === 'query' ? v.trim() !== '' : v !== ''))
