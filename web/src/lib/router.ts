// A tiny hash router (no dependency): #/ -> documents list, #/docs/:id -> editor,
// #/classic -> the original Generate + tray page (kept until W1 is done).

import { readable } from 'svelte/store'

export type Route =
  | { name: 'list' }
  | { name: 'editor'; id: string }
  | { name: 'classic' }

export function parseHash(hash: string): Route {
  const path = hash.replace(/^#/, '') || '/'
  if (path === '/classic') return { name: 'classic' }
  const m = /^\/docs\/([A-Za-z0-9-]+)$/.exec(path)
  if (m) return { name: 'editor', id: m[1] }
  return { name: 'list' }
}

export const route = readable<Route>(parseHash(globalThis.location?.hash ?? ''), (set) => {
  const on = () => set(parseHash(globalThis.location.hash))
  globalThis.addEventListener('hashchange', on)
  return () => globalThis.removeEventListener('hashchange', on)
})

export function navigate(path: string): void {
  globalThis.location.hash = path
}
