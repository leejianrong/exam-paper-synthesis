import { describe, expect, it } from 'vitest'
import { render } from '@testing-library/svelte'
import { splitMath } from './mathText'
import MathText from './MathText.svelte'

describe('splitMath', () => {
  it('splits authored inline maths out of question text', () => {
    expect(splitMath('Find the value of \\(5n - 7\\) when \\(n = 9\\).')).toEqual([
      { math: false, value: 'Find the value of ' },
      { math: true, value: '5n - 7' },
      { math: false, value: ' when ' },
      { math: true, value: 'n = 9' },
      { math: false, value: '.' },
    ])
    expect(splitMath('No maths here.')).toEqual([{ math: false, value: 'No maths here.' }])
    expect(splitMath('\\(\\frac{3}{4}\\)')).toEqual([{ math: true, value: '\\frac{3}{4}' }])
  })
})

describe('MathText', () => {
  it('never shows the delimiters; each formula gets a math host', () => {
    const { container } = render(MathText, { text: 'A pen costs $\\(k\\). Find \\(4k\\).' })
    expect(container.textContent).not.toContain('\\(')
    const hosts = container.querySelectorAll('.math-host')
    expect([...hosts].map((h) => (h as HTMLElement).dataset.latex)).toEqual(['k', '4k'])
  })
})
