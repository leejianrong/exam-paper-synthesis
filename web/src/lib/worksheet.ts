// Ephemeral, client-side "current worksheet" store (V4). No server route and no
// persistence — reloading the page clears it (honors ADR-0001: single-user,
// ephemeral). Holds the set of approved questions plus an editable title; V5
// export will read the approved objects straight from here.

import { derived, get, writable } from 'svelte/store'

import type { Question } from './types'

export const DEFAULT_TITLE = 'Untitled worksheet'

export interface Worksheet {
  title: string
  items: Question[]
}

function createWorksheet() {
  const store = writable<Worksheet>({ title: DEFAULT_TITLE, items: [] })
  const { subscribe, update, set } = store

  /** Add a question, deduped by `id` (a question already added is ignored). */
  function add(q: Question): void {
    update((w) =>
      w.items.some((item) => item.id === q.id) ? w : { ...w, items: [...w.items, q] },
    )
  }

  /** Remove the question with the given `id` (no-op if absent). */
  function remove(id: string): void {
    update((w) => ({ ...w, items: w.items.filter((item) => item.id !== id) }))
  }

  /** Move an item one slot up or down, clamped at both ends. */
  function move(id: string, dir: 'up' | 'down'): void {
    update((w) => {
      const from = w.items.findIndex((item) => item.id === id)
      if (from === -1) return w
      const to = dir === 'up' ? from - 1 : from + 1
      if (to < 0 || to >= w.items.length) return w
      const items = [...w.items]
      ;[items[from], items[to]] = [items[to], items[from]]
      return { ...w, items }
    })
  }

  /** Set the worksheet title (used by V5 export). */
  function setTitle(title: string): void {
    update((w) => ({ ...w, title }))
  }

  /** True when a question with `id` is already in the worksheet. */
  function has(id: string): boolean {
    return get(store).items.some((item) => item.id === id)
  }

  /** Reset to an empty, default-titled worksheet. */
  function clear(): void {
    set({ title: DEFAULT_TITLE, items: [] })
  }

  return { subscribe, add, remove, move, setTitle, has, clear }
}

export const worksheet = createWorksheet()

/** Running total marks = sum of `question.total_marks` across approved items. */
export const totalMarks = derived(worksheet, (w) =>
  w.items.reduce((sum, item) => sum + item.question.total_marks, 0),
)
