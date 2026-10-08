// Debounced autosave with optimistic concurrency (W1c). A stale save (409) is a
// conflict the user resolves by reloading — never silently merged.

import { writable, type Readable } from 'svelte/store'
import { ApiError } from './docsApi'
import type { PaperDocument } from './doc'

export type SaveStatus = 'saved' | 'dirty' | 'saving' | 'conflict' | 'error'

export interface Autosaver {
  status: Readable<SaveStatus>
  /** Queue `doc` to be saved after the debounce delay. */
  schedule(doc: PaperDocument): void
  /** Save any pending change now; resolves when nothing is left in flight. */
  flush(): Promise<void>
  /** The version the next save is based on. */
  version(): number
  dispose(): void
}

export interface AutosaveOptions {
  save: (doc: PaperDocument, baseVersion: number) => Promise<{ version: number }>
  initialVersion: number
  delayMs?: number
}

export function createAutosaver(opts: AutosaveOptions): Autosaver {
  const delay = opts.delayMs ?? 1000
  const status = writable<SaveStatus>('saved')
  let version = opts.initialVersion
  let pending: PaperDocument | null = null
  let timer: ReturnType<typeof setTimeout> | null = null
  let inflight: Promise<void> | null = null
  let stopped = false // conflict or dispose: no further saves

  function clearTimer() {
    if (timer) clearTimeout(timer)
    timer = null
  }

  async function run(): Promise<void> {
    while (pending && !stopped) {
      const doc = pending
      pending = null
      status.set('saving')
      try {
        const saved = await opts.save(doc, version)
        version = saved.version
        status.set(pending ? 'dirty' : 'saved')
      } catch (e) {
        if (e instanceof ApiError && e.status === 409) {
          stopped = true
          pending = null
          status.set('conflict')
        } else {
          pending = pending ?? doc // keep the unsaved change for a retry
          status.set('error')
          return
        }
      }
    }
  }

  function start(): Promise<void> {
    if (!inflight) {
      inflight = run().finally(() => {
        inflight = null
      })
    }
    return inflight
  }

  return {
    status: { subscribe: status.subscribe },
    schedule(doc) {
      if (stopped) return
      pending = doc
      status.set(inflight ? 'saving' : 'dirty')
      clearTimer()
      timer = setTimeout(() => {
        timer = null
        void start()
      }, delay)
    },
    async flush() {
      clearTimer()
      await start()
    },
    version: () => version,
    dispose() {
      stopped = true
      clearTimer()
    },
  }
}
