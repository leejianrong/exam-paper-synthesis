// Starter paper templates (P4): ordinary documents — sections with a mode, a marks target and
// instructions, plus the paper time — that the teacher then fills and edits like any other.
// Nothing here is special-cased in the engine; a template is only a document made up front.
import { buildDocument, type DocJSON, type PaperDocument } from './doc'
import type { PaperSettings } from './layout'
import { sectionNode } from './sections'

export interface PaperTemplate {
  id: string
  label: string
  title: string
  settings: PaperSettings
  sections: ReturnType<typeof sectionNode>[]
}

export const PAPER_TEMPLATES: PaperTemplate[] = [
  {
    id: 'p1-a',
    label: 'Paper 1 · Booklet A',
    title: 'Paper 1 Booklet A',
    settings: { time_min: 60 },
    sections: [
      sectionNode('Booklet A', {
        mode: 'mcq',
        marks_target: 20,
        instructions: 'For each question, choose the correct answer.',
      }),
    ],
  },
  {
    id: 'p1-b',
    label: 'Paper 1 · Booklet B',
    title: 'Paper 1 Booklet B',
    settings: { time_min: 60 },
    sections: [
      sectionNode('Booklet B', {
        mode: 'short',
        marks_target: 25,
        instructions: 'Write your answer in the space provided.',
      }),
    ],
  },
  {
    id: 'p2',
    label: 'Paper 2',
    title: 'Paper 2',
    settings: { time_min: 90 },
    sections: [
      sectionNode('Section A', {
        mode: 'short',
        marks_target: 10,
        instructions: 'Write your answer in the space provided.',
      }),
      sectionNode('Section B', {
        mode: 'structured',
        marks_target: 45,
        instructions: 'Show your working clearly.',
      }),
    ],
  },
]

export function buildFromTemplate(t: PaperTemplate): PaperDocument {
  const content: DocJSON = { type: 'doc', content: t.sections }
  return buildDocument(t.title, content, t.settings)
}
