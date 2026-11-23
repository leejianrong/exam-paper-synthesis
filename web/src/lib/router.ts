// A tiny hash router (no dependency): #/ -> documents list, #/docs/:id -> editor,
// #/classic -> the original Generate + tray page (hidden unless turned on in Settings, O1),
// #/settings -> the account's settings, #/bank -> the question bank (EXA-167).

import { readable } from 'svelte/store'

export type Route =
  | { name: 'list' }
  | { name: 'editor'; id: string }
  | { name: 'classic' }
  | { name: 'settings' }
  | { name: 'bank' }
  | { name: 'login'; error: string }

export function parseHash(hash: string): Route {
  const [path, query = ''] = (hash.replace(/^#/, '') || '/').split('?')
  if (path === '/login') return { name: 'login', error: new URLSearchParams(query).get('error') ?? '' }
  if (path === '/classic') return { name: 'classic' }
  if (path === '/settings') return { name: 'settings' }
  if (path === '/bank') return { name: 'bank' }
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
