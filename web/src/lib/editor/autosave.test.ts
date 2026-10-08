import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { get } from 'svelte/store'
import { createAutosaver } from './autosave'
import { ApiError } from './docsApi'
import type { PaperDocument } from './doc'

const doc = (title: string): PaperDocument => ({
  schema_version: '1.0.0',
  title,
  content: { type: 'doc', content: [] },
})

beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

describe('autosaver', () => {
  it('debounces: only the latest doc is saved, with the base version', async () => {
    const save = vi.fn().mockResolvedValue({ version: 8 })
    const a = createAutosaver({ save, initialVersion: 7, delayMs: 1000 })
    a.schedule(doc('a'))
    await vi.advanceTimersByTimeAsync(500)
    a.schedule(doc('b'))
    expect(get(a.status)).toBe('dirty')
    await vi.advanceTimersByTimeAsync(999)
    expect(save).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(1)
    expect(save).toHaveBeenCalledTimes(1)
    expect(save).toHaveBeenCalledWith(doc('b'), 7)
    expect(get(a.status)).toBe('saved')
    expect(a.version()).toBe(8)
  })

  it('chains the next save on the returned version', async () => {
    const save = vi.fn().mockResolvedValueOnce({ version: 2 }).mockResolvedValueOnce({ version: 3 })
    const a = createAutosaver({ save, initialVersion: 1, delayMs: 10 })
    a.schedule(doc('a'))
    await vi.advanceTimersByTimeAsync(10)
    a.schedule(doc('b'))
    await vi.advanceTimersByTimeAsync(10)
    expect(save.mock.calls.map((c) => c[1])).toEqual([1, 2])
    expect(a.version()).toBe(3)
  })

  it('a change made while saving is saved afterwards', async () => {
    let release: (v: { version: number }) => void = () => {}
    const save = vi
      .fn()
      .mockImplementationOnce(() => new Promise((r) => (release = r)))
      .mockResolvedValueOnce({ version: 3 })
    const a = createAutosaver({ save, initialVersion: 1, delayMs: 10 })
    a.schedule(doc('a'))
    await vi.advanceTimersByTimeAsync(10)
    expect(get(a.status)).toBe('saving')
    a.schedule(doc('b')) // arrives mid-flight
    release({ version: 2 })
    await vi.advanceTimersByTimeAsync(10)
    expect(save).toHaveBeenCalledTimes(2)
    expect(save.mock.calls[1]).toEqual([doc('b'), 2])
    expect(get(a.status)).toBe('saved')
  })

  it('flush saves immediately', async () => {
    const save = vi.fn().mockResolvedValue({ version: 2 })
    const a = createAutosaver({ save, initialVersion: 1, delayMs: 60_000 })
    a.schedule(doc('a'))
    await a.flush()
    expect(save).toHaveBeenCalledTimes(1)
    expect(get(a.status)).toBe('saved')
  })

  it('a 409 is a conflict: no retry, no further saves', async () => {
    const save = vi.fn().mockRejectedValue(new ApiError(409, { current_version: 5 }))
    const a = createAutosaver({ save, initialVersion: 1, delayMs: 10 })
    a.schedule(doc('a'))
    await vi.advanceTimersByTimeAsync(10)
    expect(get(a.status)).toBe('conflict')
    a.schedule(doc('b'))
    await vi.advanceTimersByTimeAsync(1000)
    await a.flush()
    expect(save).toHaveBeenCalledTimes(1)
    expect(get(a.status)).toBe('conflict')
  })

  it('other errors keep the change and retry on the next schedule', async () => {
    const save = vi
      .fn()
      .mockRejectedValueOnce(new ApiError(500, 'boom'))
      .mockResolvedValueOnce({ version: 2 })
    const a = createAutosaver({ save, initialVersion: 1, delayMs: 10 })
    a.schedule(doc('a'))
    await vi.advanceTimersByTimeAsync(10)
    expect(get(a.status)).toBe('error')
    await a.flush() // the unsaved change is still pending
    expect(save).toHaveBeenCalledTimes(2)
    expect(save.mock.calls[1]).toEqual([doc('a'), 1])
    expect(get(a.status)).toBe('saved')
  })

  it('dispose stops saving', async () => {
    const save = vi.fn().mockResolvedValue({ version: 2 })
    const a = createAutosaver({ save, initialVersion: 1, delayMs: 10 })
    a.schedule(doc('a'))
    a.dispose()
    await vi.advanceTimersByTimeAsync(100)
    expect(save).not.toHaveBeenCalled()
  })
})
