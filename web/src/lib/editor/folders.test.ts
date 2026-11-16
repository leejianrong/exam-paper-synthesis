import { describe, it, expect } from 'vitest'
import { groupByFolder, paperPart, partOf } from './folders'

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

describe('paperPart', () => {
  it('reads the part from template and generated titles', () => {
    expect(paperPart('Paper 1 Booklet A')).toBe('booklet_a')
    expect(paperPart('P6 Paper 1 Booklet B')).toBe('booklet_b')
    expect(paperPart('P5 Paper 2')).toBe('paper_2')
    expect(paperPart('Prelim booklet a (copy)')).toBe('booklet_a')
  })

  it('is none of the three for other titles', () => {
    expect(paperPart('Ratio review')).toBeNull()
    expect(paperPart('Paper 12 drill')).toBeNull()
    expect(paperPart('Booklets and more')).toBeNull()
    expect(paperPart('')).toBeNull()
  })
})

describe('partOf', () => {
  it('prefers the server’s paper_part (from the cover) over the title', () => {
    expect(partOf({ ...doc('1', 'Term 3 practice'), paper_part: 'booklet_b' })).toBe('booklet_b')
    // null from the server means none of the three, even if the title says otherwise
    expect(partOf({ ...doc('2', 'Paper 2 notes'), paper_part: null })).toBeNull()
    // an older server without the field: the title decides
    expect(partOf(doc('3', 'P6 Paper 2'))).toBe('paper_2')
  })

  it('a renamed paper still fills its folder chip', () => {
    const { groups } = groupByFolder([folder('a', 'A')], [{ ...doc('1', 'Mock', 'a'), paper_part: 'booklet_a' }])
    expect([...groups[0].parts]).toEqual(['booklet_a'])
  })
})

describe('groupByFolder', () => {
  it('keeps folder and paper order, collects parts, and unfiles unknown folders', () => {
    const { groups, unfiled } = groupByFolder(
      [folder('b', 'Beta'), folder('a', 'Alpha')],
      [doc('1', 'P6 Paper 2', 'a'), doc('2', 'Drill'), doc('3', 'Paper 1 Booklet A', 'a'), doc('4', 'X', 'zz')],
    )
    expect(groups.map((g) => g.folder.id)).toEqual(['b', 'a'])
    expect(groups[0].docs).toEqual([])
    expect(groups[1].docs.map((d) => d.id)).toEqual(['1', '3'])
    expect([...groups[1].parts].sort()).toEqual(['booklet_a', 'paper_2'])
    expect(unfiled.map((d) => d.id)).toEqual(['2', '4'])
  })
})
