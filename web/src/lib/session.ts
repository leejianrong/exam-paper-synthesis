// Who is signed in (W3). The API owns identity (a session cookie it sets); the SPA only asks
// `/auth/me` and shows a login page when the answer is "nobody".

import { writable } from 'svelte/store'
import { fail, offline } from './errors'

const BASE: string = import.meta.env.VITE_API ?? 'http://localhost:8000'

/** `fetch` with the cookie; an unreachable server is an `ApiError(0)` (as `http.reach`, which
 *  can't be imported here: http.ts imports this module). */
const send = (url: string, init: RequestInit = {}): Promise<Response> =>
  fetch(url, { ...init, credentials: 'include' }).catch((e: unknown) => {
    throw offline(e)
  })

export interface SessionUser {
  id: string
  email: string | null
  name: string | null
  /** The local development stub (no sign-in, no sign-out). */
  dev: boolean
}

export type SessionState = { status: 'loading' } | { status: 'anon' } | { status: 'user'; user: SessionUser }

export const session = writable<SessionState>({ status: 'loading' })

export async function loadSession(): Promise<void> {
  try {
    const res = await fetch(`${BASE}/auth/me`, { credentials: 'include' })
    if (res.ok) session.set({ status: 'user', user: (await res.json()) as SessionUser })
    else session.set({ status: 'anon' })
  } catch {
    // API unreachable: show the app's own errors rather than a login page that cannot work.
    session.set({ status: 'anon' })
  }
}

/** The API said 401: whoever we thought was signed in is not (expired or signed out). */
export function sessionLost(): void {
  session.set({ status: 'anon' })
}

export async function signOut(): Promise<void> {
  try {
    await fetch(`${BASE}/auth/logout`, { method: 'POST', credentials: 'include' })
  } finally {
    session.set({ status: 'anon' })
  }
}

export interface ProviderInfo {
  name: string
  label: string
}

export async function loadProviders(): Promise<{ providers: ProviderInfo[]; dev: boolean }> {
  const res = await send(`${BASE}/auth/providers`)
  if (!res.ok) return fail(res)
  return (await res.json()) as { providers: ProviderInfo[]; dev: boolean }
}

export function loginUrl(provider: string): string {
  return `${BASE}/auth/${encodeURIComponent(provider)}/login`
}

export interface Quota {
  per_day: number
  /** Exports left in the rolling 24 h, or `null` when the account is unlimited. */
  left_day: number | null
}

export async function loadQuota(): Promise<Quota | null> {
  try {
    const res = await fetch(`${BASE}/auth/quota`, { credentials: 'include' })
    return res.ok ? ((await res.json()) as Quota) : null
  } catch {
    return null
  }
}

/** The caller's data as a zip (W5 privacy promise). Throws on a non-2xx answer. */
export async function exportAccountData(): Promise<Blob> {
  const res = await send(`${BASE}/account/export`)
  if (!res.ok) return fail(res)
  return res.blob()
}

/** Erase the account and everything in it; the caller must have asked the user to confirm. */
export async function deleteAccount(): Promise<void> {
  const res = await send(`${BASE}/account`, {
    method: 'DELETE',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ confirm: 'DELETE' }),
  })
  if (!res.ok) return fail(res)
  session.set({ status: 'anon' })
}
