// What the inspector panel says about a block (EXA-93). Status, provenance and metadata
// live here, beside the page — never on it — so the page shows only what prints.

import type { Question } from '../types'
import type { DocNode } from './doc'

export interface Facts {
  heading: string
  /** One line on how far the content can be trusted. */
  status: { text: string; tone: 'ok' | 'warn' | 'plain' }
  rows: Array<[label: string, value: string]>
}

const cap = (s: string): string => s.charAt(0).toUpperCase() + s.slice(1)

export function describeBlock(node: DocNode, number: number): Facts {
  if (node.type === 'freeformQuestion') {
    const marks = node.attrs?.marks as number | null | undefined
    return {
      heading: `Question ${number}`,
      status: { text: 'Free-form — written by you, not checked by the engine', tone: 'plain' },
      rows: [
        ['Type', 'Free-form'],
        ['Marks', marks === null || marks === undefined ? 'Not set' : String(marks)],
      ],
    }
  }
  const q = node.attrs?.question as Question
  const rows: Facts['rows'] = [['Marks', String(q.question.total_marks)]]
  if (q.source_type === 'sourced') {
    const reviewed = Boolean(q.validation.checks?.human_reviewed)
    return {
      heading: `Question ${number}`,
      status: reviewed
        ? { text: 'From your bank — reviewed by you', tone: 'ok' }
        : { text: 'From your bank — not yet reviewed', tone: 'warn' },
      rows: [['Type', 'From my bank'], ...rows, ['Id', q.id]],
    }
  }
  const verified = q.validation.status === 'pass'
  if (q.cognitive?.difficulty) rows.push(['Difficulty', cap(q.cognitive.difficulty)])
  rows.push(['Blueprint', q.blueprint_code], ['Seed', String(q.seed)])
  if (q.parent_id) rows.push(['Edited from', q.parent_id])
  return {
    heading: `Question ${number}`,
    status: verified
      ? { text: 'Engine-verified — the answer key is the solution to this question', tone: 'ok' }
      : { text: 'Not verified', tone: 'warn' },
    rows: [['Type', 'Generated'], ...rows],
  }
}

export interface Summary {
  questions: number
  generated: number
  bank: number
  freeform: number
  remarks: number
  marks: number
}

export function summarise(blocks: DocNode[], marks: number): Summary {
  const kind = (n: DocNode) =>
    n.type === 'freeformQuestion'
      ? 'freeform'
      : (n.attrs?.question as Question)?.source_type === 'sourced'
        ? 'bank'
        : 'generated'
  return {
    questions: blocks.length,
    generated: blocks.filter((b) => kind(b) === 'generated').length,
    bank: blocks.filter((b) => kind(b) === 'bank').length,
    freeform: blocks.filter((b) => kind(b) === 'freeform').length,
    remarks: blocks.filter((b) => typeof b.attrs?.remark === 'string' && b.attrs.remark.trim()).length,
    marks,
  }
}
