// What the print preview's paginator decided (P6d): which questions fall on which printed page and
// what each page's tally box adds up to. Read from the preview document itself, so it is exactly
// what the PDF will print; the editor does not try to guess page breaks from its own layout.

export interface PageInfo {
  page: number // the printed page number: the cover counts as page 1 (EXA-138)
  first: number | null // first / last question number on the page (null: no question)
  last: number | null
  continued: boolean // the page opens with the rest of a question that began earlier
  marks: number // the tally box total; 0 when the page has none
  kind?: 'cover' | 'blank' | 'rough' // a page of its own (P7) rather than questions
}

export interface PageSummary {
  paginated: boolean // false: the preview was not paginated (every paper is since EXA-138)
  pages: PageInfo[]
  warnings: number // questions whose working space had to be trimmed to fit a page
}

/** `start` is the paper's first question number (Booklet B carries on from Booklet A). */
export function summarisePages(doc: Document, start = 1): PageSummary {
  const warnings = Number(doc.documentElement.getAttribute('data-pagination-warnings') ?? 0)
  const boxes = Array.from(doc.querySelectorAll('.pg'))
  let running = start - 1
  const pages = boxes.map((box, i) => {
    const numbers: number[] = []
    let continued = false
    box.querySelectorAll('.question').forEach((q, k) => {
      if (q.classList.contains('cont')) {
        if (k === 0) continued = true
      } else running += 1
      numbers.push(running)
    })
    const tally = box.querySelector('.tally-total')?.textContent
    const kind: PageInfo['kind'] = box.querySelector('.cover-page')
      ? 'cover'
      : box.querySelector('.blank-page.rough')
        ? 'rough'
        : box.querySelector('.blank-page')
          ? 'blank'
          : undefined
    return {
      ...(kind && !numbers.length ? { kind } : {}),
      page: i + 1,
      first: numbers.length ? numbers[0] : null,
      last: numbers.length ? numbers[numbers.length - 1] : null,
      continued,
      marks: Number(tally) || 0,
    }
  })
  return { paginated: boxes.length > 0, pages, warnings }
}

export function describePage(p: PageInfo): string {
  const own = { cover: 'cover page', blank: 'blank page', rough: 'rough work' }
  const range =
    p.first === null
      ? p.kind
        ? own[p.kind]
        : 'no questions'
      : p.first === p.last
        ? `Q${p.first}${p.continued ? ' (continued)' : ''}`
        : `Q${p.first}–${p.last}${p.continued ? ' (starts mid-Q' + p.first + ')' : ''}`
  return p.marks ? `${range} · ${p.marks} mark${p.marks === 1 ? '' : 's'}` : range
}
