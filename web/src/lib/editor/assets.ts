// Image assets (W2b): upload and URLs. The server validates the bytes (PNG/JPEG only, size
// and quota limits); here we only send them and report its reason when it refuses.

const BASE: string = import.meta.env.VITE_API ?? 'http://localhost:8000'

export interface AssetMeta {
  id: string
  mime: string
  width: number
  height: number
  bytes: number
}

/** Where the browser loads an asset from. (Dev: the default owner, as `<img>` cannot send the dev header.) */
export function assetUrl(id: string): string {
  return `${BASE}/assets/${encodeURIComponent(id)}`
}

export async function uploadAsset(file: Blob, filename = 'image'): Promise<AssetMeta> {
  const res = await fetch(`${BASE}/assets`, {
    method: 'POST',
    headers: { 'x-filename': filename },
    body: file,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = (await res.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      /* keep statusText */
    }
    throw new Error(`Could not upload the image: ${detail}`)
  }
  return (await res.json()) as AssetMeta
}

export const IMAGE_TYPES = ['image/png', 'image/jpeg']

/** Image files from a DataTransfer (clipboard or drop), PNG/JPEG only. */
export function imageFiles(data: DataTransfer | null | undefined): File[] {
  return Array.from(data?.files ?? []).filter((f) => IMAGE_TYPES.includes(f.type))
}
