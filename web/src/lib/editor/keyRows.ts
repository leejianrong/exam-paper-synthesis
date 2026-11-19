// The answer key view (EXA-162) shows the server's printed key, so finding a question in it
// means reading that markup: the school key labels its rows and grid columns "Q16"; worked
// solutions are an <ol class="questions"> with one <li> per question left in the key, in order.

import type { DocNode } from './doc'
import { hasContent } from './paperReport'

const LABEL = /^Q(\d+)$/

const labelNumber = (cell: Element | null | undefined): number | null => {
  const m = LABEL.exec(cell?.textContent?.trim() ?? '')
  return m ? Number(m[1]) : null
}

/** The paper numbers that print in the key, in order (a left-out question keeps its number). */
export function keyNumbers(blocks: DocNode[], start: number): number[] {
  return blocks.flatMap((b, i) => (b.attrs?.in_key === false ? [] : [start + i]))
}

/** Where question `n` is in a printed key: a grid column head, a table row label, or a worked
 *  solution. Null when it isn't there (left out, or not drawn yet). */
export function findKeyRow(doc: Document, n: number, numbers: number[]): HTMLElement | null {
  for (const th of doc.querySelectorAll<HTMLElement>('th[scope]')) {
    if (labelNumber(th) === n) return th
  }
  const i = numbers.indexOf(n)
  if (i < 0) return null
  return doc.querySelectorAll<HTMLElement>('ol.questions > li.question')[i] ?? null
}

/** Which question a click in the printed key landed on, or null. */
export function keyRowNumber(target: Element, numbers: number[]): number | null {
  const li = target.closest('ol.questions > li.question')
  if (li) {
    const i = Array.from(li.parentElement?.children ?? []).filter((c) => c.matches('li.question')).indexOf(li)
    return numbers[i] ?? null
  }
  const cell = target.closest('th, td')
  const row = cell?.closest('tr')
  if (!cell || !row) return null
  const table = row.closest('table')
  if (table?.classList.contains('key-grid')) {
    // the number heads the column: the same cell index in the table's first row
    const col = Array.from(row.children).indexOf(cell)
    return labelNumber(table.rows[0]?.cells[col])
  }
  if (table?.classList.contains('key-pairs')) {
    // two questions to a row: a label cell and its answer cell
    return labelNumber(cell.matches('th') ? cell : cell.previousElementSibling)
  }
  return labelNumber(row.querySelector('th[scope="row"]'))
}

/** A teacher's own question has its answer written (every part's, when it has parts). */
export function answerWritten(block: DocNode): boolean {
  const parts = (block.content ?? []).filter((c) => c.type === 'freeformPart')
  const answers = parts.length ? parts.map((p) => p.attrs?.answer) : [block.attrs?.answer]
  return answers.every((a) => hasContent((a as { content?: DocNode[] } | undefined)?.content))
}
