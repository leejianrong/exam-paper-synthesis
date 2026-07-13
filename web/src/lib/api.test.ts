import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { generate, editQuestion, previewWorksheet, exportPdf } from './api'
import type { Question } from './types'

// A minimal canonical object; only `id` is read back by the SPA in these paths.
const fakeQuestion = { id: 'q1' } as Question

function okResponse(body: unknown): Response {
  return {
    ok: true,
    status: 200,
    json: async () => body,
  } as unknown as Response
}

function errResponse(status: number, detail: string): Response {
  return {
    ok: false,
    status,
    text: async () => detail,
  } as unknown as Response
}

function htmlResponse(html: string): Response {
  return {
    ok: true,
    status: 200,
    text: async () => html,
  } as unknown as Response
}

function blobResponse(blob: Blob): Response {
  return {
    ok: true,
    status: 200,
    blob: async () => blob,
  } as unknown as Response
}

const fetchMock = vi.fn()

beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
})

describe('generate', () => {
  it('POSTs to {BASE}/generate with the blueprint code + count and returns .questions', async () => {
    fetchMock.mockResolvedValue(okResponse({ questions: [fakeQuestion] }))

    const result = await generate('ratio_medium', 3)

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    // Default base when VITE_API is unset.
    expect(url).toBe('http://localhost:8000/generate')
    expect(init.method).toBe('POST')
    expect(init.headers).toMatchObject({ 'content-type': 'application/json' })
    expect(JSON.parse(init.body as string)).toEqual({
      blueprint_code: 'ratio_medium',
      count: 3,
    })
    expect(result).toEqual([fakeQuestion])
  })

  it('defaults count to 1', async () => {
    fetchMock.mockResolvedValue(okResponse({ questions: [] }))
    await generate('ratio_medium')
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(JSON.parse(init.body as string)).toEqual({
      blueprint_code: 'ratio_medium',
      count: 1,
    })
  })

  it('throws "API <status>: <detail>" on a non-ok response', async () => {
    fetchMock.mockResolvedValue(errResponse(422, 'infeasible'))
    await expect(generate('ratio_medium')).rejects.toThrow('API 422: infeasible')
  })

  it('honours the VITE_API base override', async () => {
    vi.stubEnv('VITE_API', 'https://api.example.test')
    vi.resetModules()
    // Re-import so the module-level BASE is recomputed from the stubbed env.
    const { generate: generateWithBase } = await import('./api')
    fetchMock.mockResolvedValue(okResponse({ questions: [] }))

    await generateWithBase('ratio_medium')

    const [url] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('https://api.example.test/generate')
  })
})

describe('editQuestion', () => {
  it('POSTs to /edit/{op} with the question + seed and returns .question', async () => {
    fetchMock.mockResolvedValue(okResponse({ question: fakeQuestion }))

    const result = await editQuestion('make-harder', fakeQuestion, 7)

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('http://localhost:8000/edit/make-harder')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toEqual({
      question: fakeQuestion,
      seed: 7,
    })
    expect(result).toBe(fakeQuestion)
  })

  it('defaults seed to null', async () => {
    fetchMock.mockResolvedValue(okResponse({ question: fakeQuestion }))
    await editQuestion('regenerate', fakeQuestion)
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(JSON.parse(init.body as string)).toEqual({
      question: fakeQuestion,
      seed: null,
    })
  })

  it('throws on a non-ok response', async () => {
    fetchMock.mockResolvedValue(errResponse(400, 'bad op'))
    await expect(editQuestion('regenerate', fakeQuestion)).rejects.toThrow('API 400: bad op')
  })
})

describe('previewWorksheet', () => {
  it('POSTs to /export/preview with {title, questions} and returns the HTML text', async () => {
    fetchMock.mockResolvedValue(htmlResponse('<main class="sheet worksheet"></main>'))

    const result = await previewWorksheet('Term 3 Ratio', [fakeQuestion])

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('http://localhost:8000/export/preview')
    expect(init.method).toBe('POST')
    expect(init.headers).toMatchObject({ 'content-type': 'application/json' })
    expect(JSON.parse(init.body as string)).toEqual({
      title: 'Term 3 Ratio',
      questions: [fakeQuestion],
    })
    expect(result).toBe('<main class="sheet worksheet"></main>')
  })

  it('throws "API <status>: <detail>" on a non-ok response', async () => {
    fetchMock.mockResolvedValue(errResponse(422, 'no questions to export'))
    await expect(previewWorksheet('T', [])).rejects.toThrow('API 422: no questions to export')
  })
})

describe('exportPdf', () => {
  it('POSTs to /export/worksheet and returns the PDF Blob', async () => {
    const pdf = new Blob([new Uint8Array([0x25, 0x50, 0x44, 0x46])], { type: 'application/pdf' })
    fetchMock.mockResolvedValue(blobResponse(pdf))

    const result = await exportPdf('worksheet', 'Term 3 Ratio', [fakeQuestion])

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('http://localhost:8000/export/worksheet')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toEqual({
      title: 'Term 3 Ratio',
      questions: [fakeQuestion],
    })
    expect(result).toBe(pdf)
    expect(result.type).toBe('application/pdf')
  })

  it('POSTs to /export/answer-key for the answer-key kind', async () => {
    const pdf = new Blob([new Uint8Array([0x25, 0x50, 0x44, 0x46])], { type: 'application/pdf' })
    fetchMock.mockResolvedValue(blobResponse(pdf))

    await exportPdf('answer-key', 'Term 3 Ratio', [fakeQuestion])

    const [url] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('http://localhost:8000/export/answer-key')
  })

  it('throws "API <status>: <detail>" on a non-ok response', async () => {
    fetchMock.mockResolvedValue(errResponse(422, 'invalid question'))
    await expect(exportPdf('worksheet', 'T', [fakeQuestion])).rejects.toThrow(
      'API 422: invalid question',
    )
  })
})
