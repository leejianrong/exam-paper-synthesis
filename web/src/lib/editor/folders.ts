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

/**
 * Which exam-set part a paper is, read from its title. The list response carries no content, and
 * the title is the one field it has that names the part: the templates and the generator title
 * papers "Paper 1 Booklet A" / "P6 Paper 1 Booklet B" / "P5 Paper 2". A paper renamed without
 * those words counts as none of the three.
 */
export function paperPart(title: string): PaperPart | null {
  if (/\bbooklet\s*a\b/i.test(title)) return 'booklet_a'
  if (/\bbooklet\s*b\b/i.test(title)) return 'booklet_b'
  if (/\bpaper\s*(2|two|ii)\b/i.test(title)) return 'paper_2'
  return null
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
    const part = paperPart(d.title)
    if (part) g.parts.add(part)
  }
  return { groups, unfiled }
}
