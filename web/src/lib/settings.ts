// The signed-in teacher's settings (O1, EXA-125), kept on the account by the API so they
// follow the teacher across devices. `null` until loaded; defaults apply when unreachable.

import { writable } from 'svelte/store'
import { apiFetch } from './http'

const BASE: string = import.meta.env.VITE_API ?? 'http://localhost:8000'

export interface Settings {
  /** Show the original Generate + tray page (off by default). */
  classic_generator: boolean
}

export const DEFAULT_SETTINGS: Settings = { classic_generator: false }

export const settings = writable<Settings | null>(null)

export async function loadSettings(): Promise<void> {
  try {
    const res = await apiFetch(`${BASE}/settings`)
    settings.set(res.ok ? ((await res.json()) as Settings) : { ...DEFAULT_SETTINGS })
  } catch {
    settings.set({ ...DEFAULT_SETTINGS })
  }
}

/** Save a change; resolves with the stored settings, or rejects with a reason. */
export async function updateSettings(patch: Partial<Settings>): Promise<Settings> {
  const res = await apiFetch(`${BASE}/settings`, {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(patch),
  })
  if (!res.ok) throw new Error(`Couldn't save the setting (${res.status}).`)
  const next = (await res.json()) as Settings
  settings.set(next)
  return next
}
