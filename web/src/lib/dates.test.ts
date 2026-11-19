import { describe, it, expect } from 'vitest'
import { editedWhen, fullDate } from './dates'

// Local times, so the expectations hold in any time zone the tests run in.
const at = (d: number, h: number, m: number) => new Date(2026, 10, d, h, m)
const iso = (d: Date) => d.toISOString()
const now = at(19, 9, 30)

describe('fullDate', () => {
  it('writes the date the en-SG way', () => {
    expect(fullDate(iso(at(19, 9, 5)))).toBe('19 Nov 2026, 9:05 am')
    expect(fullDate(iso(at(18, 16, 40)))).toBe('18 Nov 2026, 4:40 pm')
  })

  it('is empty for a bad date', () => {
    expect(fullDate('not a date')).toBe('')
  })
})

describe('editedWhen', () => {
  it('is relative for a recent edit', () => {
    expect(editedWhen(iso(at(19, 9, 30)), now)).toBe('just now')
    expect(editedWhen(iso(at(19, 9, 25)), now)).toBe('5 min ago')
    expect(editedWhen(iso(at(19, 8, 31)), now)).toBe('59 min ago')
  })

  it('says today or yesterday with the time', () => {
    expect(editedWhen(iso(at(19, 8, 5)), now)).toBe('today, 8:05 am')
    expect(editedWhen(iso(at(18, 16, 40)), now)).toBe('yesterday, 4:40 pm')
    // just after midnight, an edit late last night is yesterday, not "today"
    expect(editedWhen(iso(at(18, 23, 50)), at(19, 0, 55))).toBe('yesterday, 11:50 pm')
  })

  it('gives the full date further back', () => {
    expect(editedWhen(iso(at(17, 10, 0)), now)).toBe('17 Nov 2026, 10:00 am')
  })

  it('a time a little ahead of the clock is “just now”; a bad date is empty', () => {
    expect(editedWhen(iso(at(19, 9, 32)), now)).toBe('just now')
    expect(editedWhen('', now)).toBe('')
  })
})
