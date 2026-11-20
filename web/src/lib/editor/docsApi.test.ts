import { describe, it, expect, vi, beforeEach } from 'vitest'

const apiFetch = vi.fn()
vi.mock('../http', () => ({ apiFetch: (...a: unknown[]) => apiFetch(...a) }))

import { copyDocument, copyTitle, renameDocument, TITLE_MAX } from './docsApi'
import type { PaperDocument } from './doc'

const record = (id: string, title: string, version = 3) => ({
  id,
  title,
  version,
  total_marks: 10,
  folder_id: 'f1',
  created_at: '',
  updated_at: '',
  document: { schema_version: '1.17.0', title, content: { type: 'doc', content: [{ type: 'paragraph' }] }, settings: { x: 1 } },
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

  it('cuts “Copy of …” to the schema’s 200 characters (code points, not UTF-16 units)', async () => {
    const long = 'Ä'.repeat(150) + '😀'.repeat(60)
    expect([...copyTitle(long)]).toHaveLength(TITLE_MAX)
    expect(copyTitle(long).startsWith('Copy of ÄÄ')).toBe(true)
    expect(copyTitle('')).toBe('Copy of Untitled paper')
    apiFetch
      .mockResolvedValueOnce(ok(record('d1', long)))
      .mockResolvedValueOnce(ok(record('c1', copyTitle(long), 1)))
      .mockResolvedValueOnce(ok(record('c1', copyTitle(long), 2)))
    await copyDocument('d1')
    expect([...sent(1).body.title]).toHaveLength(200)
    expect(sent(2).body.document.title).toBe(copyTitle(long))
  })

  it('copies the content it is given (the editor) without reading the paper first', async () => {
    const doc = record('d1', 'Held in the editor').document
    apiFetch
      .mockResolvedValueOnce(ok(record('c1', 'Copy of Held in the editor', 1)))
      .mockResolvedValueOnce(ok(record('c1', 'Copy of Held in the editor', 2)))
    await copyDocument('d1', { document: doc as unknown as PaperDocument, folder_id: null })
    expect(apiFetch).toHaveBeenCalledTimes(2)
    expect(sent(0)).toMatchObject({ method: 'POST', body: { title: 'Copy of Held in the editor', folder_id: null } })
    expect(sent(1).body.document.content).toEqual(doc.content)
  })

  it('deletes the empty copy again when its save fails', async () => {
    apiFetch
      .mockResolvedValueOnce(ok(record('d1', 'Ratio quiz')))
      .mockResolvedValueOnce(ok(record('c1', 'Copy of Ratio quiz', 1)))
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: 'boom' }), { status: 500 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    await expect(copyDocument('d1')).rejects.toMatchObject({ status: 500, detail: 'boom' })
    expect(sent(3)).toMatchObject({ method: 'DELETE' })
    expect(sent(3).url).toMatch(/\/documents\/c1$/)
  })
})
