import { describe, it, expect } from 'vitest'
import { groupByFolder, paperPart } from './folders'

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
