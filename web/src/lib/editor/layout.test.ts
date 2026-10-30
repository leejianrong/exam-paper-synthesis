import { describe, expect, it } from 'vitest'
import { MAX_SPACE_MM, SPACE_PRESETS } from './layout'

describe('working space presets', () => {
  it('grow in order up to the longest the paper allows', () => {
    const mm = SPACE_PRESETS.map((p) => p.mm)
    expect(mm).toEqual([...mm].sort((a, b) => a - b))
    expect(mm.at(-1)).toBe(MAX_SPACE_MM)
  })
})
