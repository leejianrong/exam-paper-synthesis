// Who is signed in (W3). The API owns identity (a session cookie it sets); the SPA only asks
// `/auth/me` and shows a login page when the answer is "nobody".

import { writable } from 'svelte/store'

const BASE: string = import.meta.env.VITE_API ?? 'http://localhost:8000'

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
  const res = await fetch(`${BASE}/auth/providers`, { credentials: 'include' })
  if (!res.ok) throw new Error(`API ${res.status}`)
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
