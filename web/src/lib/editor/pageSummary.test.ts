import { describe, expect, it } from 'vitest'
import { describePage, summarisePages } from './pageSummary'

function paper(html: string, warnings?: number): Document {
  const doc = document.implementation.createHTMLDocument('p')
  doc.body.innerHTML = html
  if (warnings) doc.documentElement.setAttribute('data-pagination-warnings', String(warnings))
  return doc
}

const tally = (n: number) => `<div class="tally"><span class="tally-total">${n}</span></div>`

describe('summarisePages', () => {
  it('reports an unpaginated paper as such', () => {
    const s = summarisePages(paper('<section class="question"></section>'))
    expect(s).toEqual({ paginated: false, pages: [], warnings: 0 })
  })

  it('numbers the questions on each page and reads the tallies', () => {
    const s = summarisePages(
      paper(
        `<div class="pg"><section class="question"></section><section class="question"></section>${tally(5)}</div>` +
          `<div class="pg"><section class="question"></section>${tally(3)}</div>`,
        2,
      ),
    )
    expect(s.paginated).toBe(true)
    expect(s.warnings).toBe(2)
    expect(s.pages).toEqual([
      { page: 1, first: 1, last: 2, continued: false, marks: 5 },
      { page: 2, first: 3, last: 3, continued: false, marks: 3 },
    ])
    expect(s.pages.map(describePage)).toEqual(['Q1–2 · 5 marks', 'Q3 · 3 marks'])
  })

  it('does not count the continuation of a split question as a new one', () => {
    const s = summarisePages(
      paper(
        `<div class="pg"><section class="question"></section>${tally(4)}</div>` +
          `<div class="pg"><section class="question cont"></section><section class="question"></section>${tally(3)}</div>`,
      ),
    )
    expect(s.pages[1]).toMatchObject({ first: 1, last: 2, continued: true, marks: 3 })
    expect(describePage(s.pages[1])).toBe('Q1–2 (starts mid-Q1) · 3 marks')
  })

  it('copes with a page that has no questions or no tally', () => {
    const s = summarisePages(paper('<div class="pg"><div class="paper-section"></div></div>'))
    expect(describePage(s.pages[0])).toBe('no questions')
  })
})
