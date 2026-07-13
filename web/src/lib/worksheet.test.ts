import { describe, it, expect, beforeEach } from 'vitest'
import { get } from 'svelte/store'
import { worksheet, totalMarks, DEFAULT_TITLE } from './worksheet'
import type { Question } from './types'

// Minimal canonical objects — only the fields the store reads (id, question.total_marks).
function q(id: string, marks = 0): Question {
  return {
    id,
    seed: 1,
    blueprint_code: 'ratio_medium',
    validation: { status: 'pass' },
    question: { parts: [], total_marks: marks },
  }
}

const ids = () => get(worksheet).items.map((item) => item.id)

describe('worksheet store', () => {
  beforeEach(() => {
    worksheet.clear()
  })

  it('starts empty with the default title', () => {
    expect(get(worksheet)).toEqual({ title: DEFAULT_TITLE, items: [] })
    expect(get(totalMarks)).toBe(0)
  })

  describe('add', () => {
    it('appends questions', () => {
      worksheet.add(q('a'))
      worksheet.add(q('b'))
      expect(ids()).toEqual(['a', 'b'])
    })

    it('dedups by id (a question already added is ignored)', () => {
      worksheet.add(q('a', 3))
      worksheet.add(q('a', 3))
      expect(ids()).toEqual(['a'])
    })
  })

  describe('remove', () => {
    it('removes the matching id', () => {
      worksheet.add(q('a'))
      worksheet.add(q('b'))
      worksheet.remove('a')
      expect(ids()).toEqual(['b'])
    })

    it('is a no-op for an absent id', () => {
      worksheet.add(q('a'))
      worksheet.remove('zzz')
      expect(ids()).toEqual(['a'])
    })
  })

  describe('move', () => {
    beforeEach(() => {
      worksheet.add(q('a'))
      worksheet.add(q('b'))
      worksheet.add(q('c'))
    })

    it('moves an item up', () => {
      worksheet.move('b', 'up')
      expect(ids()).toEqual(['b', 'a', 'c'])
    })

    it('moves an item down', () => {
      worksheet.move('b', 'down')
      expect(ids()).toEqual(['a', 'c', 'b'])
    })

    it('is clamped: the first item cannot move up', () => {
      worksheet.move('a', 'up')
      expect(ids()).toEqual(['a', 'b', 'c'])
    })

    it('is clamped: the last item cannot move down', () => {
      worksheet.move('c', 'down')
      expect(ids()).toEqual(['a', 'b', 'c'])
    })

    it('is a no-op for an absent id', () => {
      worksheet.move('zzz', 'up')
      expect(ids()).toEqual(['a', 'b', 'c'])
    })
  })

  describe('totalMarks', () => {
    it('is 0 for the empty worksheet', () => {
      expect(get(totalMarks)).toBe(0)
    })

    it('sums question.total_marks across items', () => {
      worksheet.add(q('a', 2))
      worksheet.add(q('b', 3))
      worksheet.add(q('c', 5))
      expect(get(totalMarks)).toBe(10)
    })

    it('reacts to remove', () => {
      worksheet.add(q('a', 2))
      worksheet.add(q('b', 3))
      worksheet.remove('a')
      expect(get(totalMarks)).toBe(3)
    })
  })

  describe('setTitle', () => {
    it('updates the title without touching items', () => {
      worksheet.add(q('a'))
      worksheet.setTitle('Term 3 Ratio')
      expect(get(worksheet).title).toBe('Term 3 Ratio')
      expect(ids()).toEqual(['a'])
    })
  })

  describe('has', () => {
    it('reflects membership by id', () => {
      expect(worksheet.has('a')).toBe(false)
      worksheet.add(q('a'))
      expect(worksheet.has('a')).toBe(true)
      expect(worksheet.has('b')).toBe(false)
    })
  })

  describe('clear', () => {
    it('resets items and title to defaults', () => {
      worksheet.add(q('a', 4))
      worksheet.setTitle('Something')
      worksheet.clear()
      expect(get(worksheet)).toEqual({ title: DEFAULT_TITLE, items: [] })
      expect(get(totalMarks)).toBe(0)
    })
  })
})
