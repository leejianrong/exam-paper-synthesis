// The signed-in teacher's settings (O1, EXA-125), kept on the account by the API so they
// follow the teacher across devices. `null` until loaded; defaults apply when unreachable.

import { writable } from 'svelte/store'
import type { MarksPlacement } from './editor/layout'
import { fail } from './errors'
import { apiFetch } from './http'
import { session } from './session'

const BASE: string = import.meta.env.VITE_API ?? 'http://localhost:8000'

/** The answer key a new paper starts with (EXA-159); a saved paper keeps its own. */
export type AnswerKeyStyle = 'school' | 'worked'

/** A new paper's level (EXA-169); '' = none, so the cover's level is left blank. */
export type DefaultLevel = '' | 'P5' | 'P6'

export interface Settings {
  /** Show the original Generate + tray page (off by default). */
  classic_generator: boolean
  answer_key_style: AnswerKeyStyle
  /** EXA-169: what a new paper starts with. The API writes these into the paper it makes. */
  school_name: string
  default_level: DefaultLevel
  marks_placement: MarksPlacement
}

export const DEFAULT_SETTINGS: Settings = {
  classic_generator: false,
  answer_key_style: 'school',
  school_name: '',
  default_level: '',
  marks_placement: 'answer',
}

/** The cover's limit on the school name (document schema), which the API checks too. */
export const SCHOOL_NAME_MAX = 120

export const settings = writable<Settings | null>(null)

// Settings belong to whoever is signed in: forget them when nobody is (sign-out, a lost
// session), so the next teacher never sees the previous one's.
session.subscribe((s) => {
  if (s.status !== 'user') settings.set(null)
})

let retry: ReturnType<typeof setTimeout> | undefined

/** Load the account's settings. Until they arrive (or if the API can't be reached) the
 *  defaults apply, and a failed load is retried once a few seconds later. */
export async function loadSettings(retryMs = 4000): Promise<void> {
  clearTimeout(retry)
  try {
    const res = await apiFetch(`${BASE}/settings`)
    if (res.ok) {
      settings.set((await res.json()) as Settings)
      return
    }
    if (res.status === 401) return // signed out: the session store takes over
  } catch {
    // unreachable: fall through to the defaults and a retry
  }
  settings.set({ ...DEFAULT_SETTINGS })
  if (retryMs > 0) retry = setTimeout(() => void loadSettings(0), retryMs)
}

/** Save a change; resolves with the stored settings, or rejects with a reason. */
export async function updateSettings(patch: Partial<Settings>): Promise<Settings> {
  const res = await apiFetch(`${BASE}/settings`, {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(patch),
  })
  if (!res.ok) return fail(res)
  const next = (await res.json()) as Settings
  settings.set(next)
  return next
}
