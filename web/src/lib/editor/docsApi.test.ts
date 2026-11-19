import { describe, it, expect, vi, beforeEach } from 'vitest'

const apiFetch = vi.fn()
vi.mock('../http', () => ({ apiFetch: (...a: unknown[]) => apiFetch(...a) }))

import { copyDocument, renameDocument } from './docsApi'

const record = (id: string, title: string, version = 3) => ({
  id,
  title,
  version,
  total_marks: 10,
  folder_id: 'f1',
  created_at: '',
  updated_at: '',
  document: { schema_version: '1.16.0', title, content: { type: 'doc', content: [{ type: 'paragraph' }] }, settings: { x: 1 } },
})
const ok = (body: unknown) => new Response(JSON.stringify(body), { status: 200 })
const sent = (i: number) => {
  const [url, init] = apiFetch.mock.calls[i] as [string, RequestInit | undefined]
  return { url, method: init?.method ?? 'GET', body: init?.body ? JSON.parse(init.body as string) : undefined }
}

beforeEach(() => apiFetch.mockReset())

describe('renameDocument (EXA-166)', () => {
  it('saves the paper with the new title on its current version', async () => {
    apiFetch.mockResolvedValueOnce(ok(record('d1', 'Old'))).mockResolvedValueOnce(ok(record('d1', 'New', 4)))
    const rec = await renameDocument('d1', 'New')
    expect(rec.title).toBe('New')
    const put = sent(1)
    expect(put.method).toBe('PUT')
    expect(put.url).toMatch(/\/documents\/d1$/)
    expect(put.body.base_version).toBe(3)
    expect(put.body.document.title).toBe('New')
    expect(put.body.document.content).toEqual(record('d1', 'Old').document.content)
  })
})

describe('copyDocument (EXA-166)', () => {
  it('makes “Copy of …” in the same folder with the same content and settings', async () => {
    apiFetch
      .mockResolvedValueOnce(ok(record('d1', 'Ratio quiz')))
      .mockResolvedValueOnce(ok(record('c1', 'Copy of Ratio quiz', 1)))
      .mockResolvedValueOnce(ok(record('c1', 'Copy of Ratio quiz', 2)))
    const rec = await copyDocument('d1')
    expect(rec.id).toBe('c1')
    expect(sent(1).body).toEqual({ title: 'Copy of Ratio quiz', template: null, folder_id: 'f1' })
    const put = sent(2)
    expect(put.url).toMatch(/\/documents\/c1$/)
    expect(put.body.base_version).toBe(1)
    expect(put.body.document.title).toBe('Copy of Ratio quiz')
    expect(put.body.document.settings).toEqual({ x: 1 })
  })

  it('deletes the empty copy again when its save fails', async () => {
    apiFetch
      .mockResolvedValueOnce(ok(record('d1', 'Ratio quiz')))
      .mockResolvedValueOnce(ok(record('c1', 'Copy of Ratio quiz', 1)))
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: 'boom' }), { status: 500 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    await expect(copyDocument('d1')).rejects.toThrow('boom')
    expect(sent(3)).toMatchObject({ method: 'DELETE' })
    expect(sent(3).url).toMatch(/\/documents\/c1$/)
  })
})
