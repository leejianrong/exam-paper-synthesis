import { describe, it, expect } from 'vitest'
import { groupByFolder, titleMatches } from './folders'

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
