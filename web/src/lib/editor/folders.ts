// O2: the paper list grouped by folder; the exam-set parts the + New wizard makes.

import type { DocumentSummary } from './doc'
import type { Folder } from './docsApi'

/** The three papers of an exam set, in exam order. */
export const PARTS = [
  { key: 'booklet_a', label: 'Booklet A' },
  { key: 'booklet_b', label: 'Booklet B' },
  { key: 'paper_2', label: 'Paper 2' },
] as const

export type PaperPart = (typeof PARTS)[number]['key']

/** The paper template (GET /papers) that makes each part: the exam set and "Single paper" (O3). */
export const PART_TEMPLATES: Record<PaperPart, string> = {
  booklet_a: 'p1_booklet_a',
  booklet_b: 'p1_booklet_b',
  paper_2: 'p2',
}

/**
 * EXA-153: the order a generated exam set is filled in: the biggest slots first (they need the
 * scarce hard and medium questions), so Booklet A last. Keep in step with the engine's
 * `paper.set_fill_order` (engine/exam_engine/paper.py), which tests/test_invariants_paper.py pins
 * to this same order.
 */
export const SET_FILL_ORDER: PaperPart[] = ['paper_2', 'booklet_b', 'booklet_a']

export interface FolderGroup {
  folder: Folder
  docs: DocumentSummary[]
}

/**
 * Folders in the order given (the API's), each with its papers in list order, then the unfiled
 * papers. A paper whose folder is not in `folders` (deleted elsewhere) counts as unfiled.
 */
export function groupByFolder(
  folders: Folder[],
  docs: DocumentSummary[],
): { groups: FolderGroup[]; unfiled: DocumentSummary[] } {
  const groups = folders.map((folder) => ({ folder, docs: [] as DocumentSummary[] }))
  const byId = new Map(groups.map((g) => [g.folder.id, g]))
  const unfiled: DocumentSummary[] = []
  for (const d of docs) {
    const g = d.folder_id ? byId.get(d.folder_id) : undefined
    if (g) g.docs.push(d)
    else unfiled.push(d)
  }
  return { groups, unfiled }
}

/**
 * EXA-166: does a paper's title match the search box? Every word typed must appear somewhere in
 * the title, ignoring case and accents; an empty search matches everything.
 */
export function titleMatches(title: string, query: string): boolean {
  const fold = (s: string) => s.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase()
  const t = fold(title || 'Untitled paper')
  return fold(query)
    .split(/\s+/)
    .filter(Boolean)
    .every((w) => t.includes(w))
}

/** EXA-168: can this folder's papers print one answer key for the whole set? */
export type SetKeyStatus = { ready: true } | { ready: false; reason: string }

const listed = (names: string[]): string =>
  names.length === 1 ? names[0] : `${names.slice(0, -1).join(', ')} or ${names[names.length - 1]}`

/**
 * Whether a folder holds one complete exam set: one Booklet A, one Booklet B and one Paper 2, by
 * the server's `paper_part` (other papers in the folder don't matter). Null when the folder holds
 * no part of a set, so its menu doesn't offer a set key at all. The same rule and words as the
 * engine's `document.exam_set_order`, which the server applies again.
 */
export function setKeyStatus(docs: DocumentSummary[]): SetKeyStatus | null {
  const count = (k: PaperPart) => docs.filter((d) => d.paper_part === k).length
  if (PARTS.every((p) => count(p.key) === 0)) return null
  const doubled = PARTS.filter((p) => count(p.key) > 1).map((p) => p.label)
  if (doubled.length) {
    return { ready: false, reason: `This folder has more than one ${doubled.join(' and ')}.` }
  }
  const missing = PARTS.filter((p) => count(p.key) === 0).map((p) => p.label)
  if (missing.length) return { ready: false, reason: `This folder has no ${listed(missing)}.` }
  return { ready: true }
}
