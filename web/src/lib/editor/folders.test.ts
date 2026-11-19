import { describe, it, expect } from 'vitest'
import { groupByFolder, setKeyStatus, titleMatches } from './folders'

const doc = (id: string, title: string, folder_id: string | null = null) => ({
  id,
  title,
  folder_id,
  total_marks: 0,
  version: 1,
  created_at: '',
  updated_at: '',
})
const folder = (id: string, name: string) => ({ id, name, created_at: '', updated_at: '' })

describe('groupByFolder', () => {
  it('keeps folder and paper order and unfiles unknown folders', () => {
    const { groups, unfiled } = groupByFolder(
      [folder('b', 'Beta'), folder('a', 'Alpha')],
      [doc('1', 'P6 Paper 2', 'a'), doc('2', 'Drill'), doc('3', 'Paper 1 Booklet A', 'a'), doc('4', 'X', 'zz')],
    )
    expect(groups.map((g) => g.folder.id)).toEqual(['b', 'a'])
    expect(groups[0].docs).toEqual([])
    expect(groups[1].docs.map((d) => d.id)).toEqual(['1', '3'])
    expect(unfiled.map((d) => d.id)).toEqual(['2', '4'])
  })
})

describe('titleMatches', () => {
  it('matches every word anywhere in the title, ignoring case and accents', () => {
    expect(titleMatches('P6 Paper 1 Booklet B', 'booklet b')).toBe(true)
    expect(titleMatches('P6 Paper 1 Booklet B', '  b   p6 ')).toBe(true)
    expect(titleMatches('Révision fractions', 'revision')).toBe(true)
    expect(titleMatches('P6 Paper 2', 'booklet')).toBe(false)
  })

  it('an empty search matches all; an untitled paper is found as “Untitled paper”', () => {
    expect(titleMatches('Ratio quiz', '')).toBe(true)
    expect(titleMatches('Ratio quiz', '   ')).toBe(true)
    expect(titleMatches('', 'untitled')).toBe(true)
  })
})

describe('setKeyStatus (EXA-168)', () => {
  type Part = 'booklet_a' | 'booklet_b' | 'paper_2' | null
  const parts = (...ps: Part[]) => ps.map((p, i) => ({ ...doc(String(i), `P${i}`, 'f'), paper_part: p }))

  it('is ready with one of each part, whatever else is in the folder', () => {
    expect(setKeyStatus(parts('paper_2', null, 'booklet_b', 'booklet_a'))).toEqual({ ready: true })
  })

  it('offers nothing in a folder with no part of a set', () => {
    expect(setKeyStatus(parts(null, null))).toBeNull()
    expect(setKeyStatus([])).toBeNull()
  })

  it('names what is missing, and a doubled part before that, in the engine’s words', () => {
    expect(setKeyStatus(parts('booklet_a'))).toEqual({
      ready: false,
      reason: 'This folder has no Booklet B or Paper 2.',
    })
    expect(setKeyStatus(parts('booklet_a', 'booklet_b'))).toEqual({ ready: false, reason: 'This folder has no Paper 2.' })
    expect(setKeyStatus(parts('booklet_a', 'booklet_a', 'paper_2'))).toEqual({
      ready: false,
      reason: '“P0” and “P1” both look like Booklet A.',
    })
  })

  it('a part named on a cover wins over a title that only looks like it', () => {
    const fromCover = parts('booklet_a', 'booklet_b', 'paper_2').map((d) => ({ ...d, paper_part_source: 'cover' as const }))
    const worksheet = { ...doc('w', 'Booklet A practice', 'f'), paper_part: 'booklet_a' as const, paper_part_source: 'title' as const }
    expect(setKeyStatus([worksheet, ...fromCover])).toEqual({ ready: true })
    // two covers saying Booklet A are still two: both are named
    const second = { ...fromCover[0], id: 'x', title: 'P6 Booklet A' }
    expect(setKeyStatus([worksheet, ...fromCover, second])).toEqual({
      ready: false,
      reason: '“P0” and “P6 Booklet A” both look like Booklet A.',
    })
  })
})
