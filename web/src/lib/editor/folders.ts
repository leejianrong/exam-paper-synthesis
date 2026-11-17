// O2: the paper list grouped by folder, and which exam-set parts a folder holds.

import type { DocumentSummary } from './doc'
import type { Folder } from './docsApi'

/** The three papers of an exam set, in the order the chips show them. */
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
 * EXA-153: the order a generated exam set is filled in, as the engine's `paper.set_fill_order`:
 * the biggest slots first (they need the scarce hard and medium questions), so Booklet A last.
 */
export const SET_FILL_ORDER: PaperPart[] = ['paper_2', 'booklet_b', 'booklet_a']

/**
 * Which exam-set part a paper is, read from its title: the fallback when a summary has no
 * server-derived `paper_part` (see `partOf`). The templates and the generator title papers
 * "Paper 1 Booklet A" / "P6 Paper 1 Booklet B" / "P5 Paper 2".
 */
export function paperPart(title: string): PaperPart | null {
  if (/\bbooklet\s*a\b/i.test(title)) return 'booklet_a'
  if (/\bbooklet\s*b\b/i.test(title)) return 'booklet_b'
  if (/\bpaper\s*(2|two|ii)\b/i.test(title)) return 'paper_2'
  return null
}

/**
 * A paper's part: the server's `paper_part` (O3, read from the cover page, so a rename keeps it),
 * else the title. `null` from the server means none (it already tried the title).
 */
export function partOf(d: DocumentSummary): PaperPart | null {
  return d.paper_part === undefined ? paperPart(d.title) : d.paper_part
}

export interface FolderGroup {
  folder: Folder
  docs: DocumentSummary[]
  parts: Set<PaperPart>
}

/**
 * Folders in the order given (the API's), each with its papers in list order, then the unfiled
 * papers. A paper whose folder is not in `folders` (deleted elsewhere) counts as unfiled.
 */
export function groupByFolder(
  folders: Folder[],
  docs: DocumentSummary[],
): { groups: FolderGroup[]; unfiled: DocumentSummary[] } {
  const groups = folders.map((folder) => ({ folder, docs: [] as DocumentSummary[], parts: new Set<PaperPart>() }))
  const byId = new Map(groups.map((g) => [g.folder.id, g]))
  const unfiled: DocumentSummary[] = []
  for (const d of docs) {
    const g = d.folder_id ? byId.get(d.folder_id) : undefined
    if (!g) {
      unfiled.push(d)
      continue
    }
    g.docs.push(d)
    const part = partOf(d)
    if (part) g.parts.add(part)
  }
  return { groups, unfiled }
}
