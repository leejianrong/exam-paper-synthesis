import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { assetUrl, imageFiles, uploadAsset } from './assets'

const fetchMock = vi.fn()
beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => vi.unstubAllGlobals())

describe('assets client', () => {
  it('posts the raw bytes with the filename and returns the metadata', async () => {
    const meta = { id: 'a'.repeat(32), mime: 'image/png', width: 2, height: 3, bytes: 9 }
    fetchMock.mockResolvedValue({ ok: true, status: 201, json: async () => meta })
    const file = new File([new Uint8Array([1, 2, 3])], 'fig.png', { type: 'image/png' })
    expect(await uploadAsset(file, 'fig.png')).toEqual(meta)
    const [url, init] = fetchMock.mock.calls[0]
    expect(String(url)).toMatch(/\/assets$/)
    expect(init.method).toBe('POST')
    expect(init.headers['x-filename']).toBe('fig.png')
    expect(init.body).toBe(file)
  })

  it("reports the server's reason when it refuses the image", async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 422,
      statusText: 'Unprocessable',
      json: async () => ({ detail: 'only PNG and JPEG images are accepted' }),
    })
    await expect(uploadAsset(new Blob(['x']))).rejects.toThrow(
      'Could not upload the image: only PNG and JPEG images are accepted',
    )
  })

  it('falls back to the status text when the error has no body', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Server Error',
      json: async () => {
        throw new Error('no json')
      },
    })
    await expect(uploadAsset(new Blob(['x']))).rejects.toThrow('Server Error')
  })

  it('builds asset URLs and keeps only PNG/JPEG files', () => {
    expect(assetUrl('abc 1')).toMatch(/\/assets\/abc%201$/)
    const files = [
      new File(['x'], 'a.png', { type: 'image/png' }),
      new File(['x'], 'b.gif', { type: 'image/gif' }),
      new File(['x'], 'c.svg', { type: 'image/svg+xml' }),
      new File(['x'], 'd.jpg', { type: 'image/jpeg' }),
    ]
    const dt = { files } as unknown as DataTransfer
    expect(imageFiles(dt).map((f) => f.name)).toEqual(['a.png', 'd.jpg'])
    expect(imageFiles(null)).toEqual([])
  })
})
