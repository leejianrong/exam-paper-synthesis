import { describe, it, expect } from 'vitest'
import { parseHash } from './router'

describe('parseHash', () => {
  it('routes the list, an editor id, and the classic page', () => {
    expect(parseHash('')).toEqual({ name: 'list' })
    expect(parseHash('#/')).toEqual({ name: 'list' })
    expect(parseHash('#/docs/9af63707-e84d')).toEqual({ name: 'editor', id: '9af63707-e84d' })
    expect(parseHash('#/classic')).toEqual({ name: 'classic' })
  })
  it('falls back to the list for anything else (no path injection)', () => {
    expect(parseHash('#/docs/../../x')).toEqual({ name: 'list' })
    expect(parseHash('#/docs/')).toEqual({ name: 'list' })
    expect(parseHash('#/nope')).toEqual({ name: 'list' })
  })
})
