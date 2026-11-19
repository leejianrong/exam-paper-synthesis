// Debounced autosave with optimistic concurrency (W1c). A stale save (409) is a
// conflict the user resolves by reloading — never silently merged.

import { writable, type Readable } from 'svelte/store'
import { ApiError } from '../errors'
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
  /** The server saved a new version itself (P8d swap/regenerate): base the next save on it,
   *  and forget any change scheduled (or conflict met) before it. */
  rebase(version: number): void
  dispose(): void
}

export interface AutosaveOptions {
  save: (doc: PaperDocument, baseVersion: number) => Promise<{ version: number }>
  initialVersion: number
  delayMs?: number
  /** Why a save failed (status 'error'); a 409 is the 'conflict' status instead. */
  onError?: (e: unknown) => void
}

export function createAutosaver(opts: AutosaveOptions): Autosaver {
  const delay = opts.delayMs ?? 1000
  const status = writable<SaveStatus>('saved')
  let version = opts.initialVersion
  let pending: PaperDocument | null = null
  let timer: ReturnType<typeof setTimeout> | null = null
  let inflight: Promise<void> | null = null
  let stopped = false // conflict or dispose: no further saves
  let disposed = false
  // Bumped by rebase(): a save in flight across it belongs to the old version, so its
  // outcome (a new version, a conflict) is ignored.
  let epoch = 0

  function clearTimer() {
    if (timer) clearTimeout(timer)
    timer = null
  }

  async function run(): Promise<void> {
    while (pending && !stopped) {
      const doc = pending
      pending = null
      status.set('saving')
      const mine = epoch
      try {
        const saved = await opts.save(doc, version)
        if (mine !== epoch) continue
        version = saved.version
        status.set(pending ? 'dirty' : 'saved')
      } catch (e) {
        if (mine !== epoch) continue
        if (e instanceof ApiError && e.status === 409) {
          stopped = true
          pending = null
          status.set('conflict')
        } else {
          pending = pending ?? doc // keep the unsaved change for a retry
          opts.onError?.(e)
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
    rebase(v) {
      // The server's version supersedes everything before it: drop a snapshot taken earlier
      // (saving it now would put the old document back) and any conflict it ran into.
      epoch += 1
      version = v
      pending = null
      clearTimer()
      if (!disposed) stopped = false
      status.set('saved')
    },
    dispose() {
      disposed = true
      stopped = true
      clearTimer()
    },
  }
}
