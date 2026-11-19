<script lang="ts" module>
  /** A question the strip names: its paper number and block. */
  export interface KeyQuestion {
    n: number
    blockId: string
  }
  /** How long the view waits after the last edit before it asks for the key again. */
  export const KEY_REFRESH_MS = 600
</script>

<script lang="ts">
  // The answer key view (EXA-162, UI-REDESIGN 4.4): the key exactly as it prints, drawn by the
  // server's own renderer (the paper's /preview/key, the HTML its PDF is made from), with the
  // key options in a strip above it. It refreshes a moment after each edit; the old key stays on
  // screen until the new one has loaded, so the page keeps its scroll position.
  import { onDestroy, tick, untrack } from 'svelte'
  import Icon from '../Icon.svelte'
  import type { KeyLayout, KeyOptions, KeyToggle } from './layout'
  import { findKeyRow, keyRowNumber } from './keyRows'

  let {
    active,
    revision,
    paused = false,
    load,
    empty,
    options,
    numbers,
    leftOut = [],
    own = [],
    onStyle,
    onOption,
    onInclude,
    onEditAnswer,
    onKey = () => {},
  }: {
    /** The view is on screen: it loads only then. */
    active: boolean
    /** Changes whenever the paper or its settings change (the key is then out of date). */
    revision: unknown
    /** A server operation is rewriting the paper: wait for it. */
    paused?: boolean
    /** The printed key's HTML, for the paper as saved (the caller saves pending edits first). */
    load: () => Promise<string>
    /** The paper has no questions yet. */
    empty: boolean
    options: Required<KeyOptions>
    /** The paper numbers that print in the key, in order. */
    numbers: number[]
    /** Questions left out of the key. */
    leftOut?: KeyQuestion[]
    /** The teacher's own questions in the key: their answers are written here. */
    own?: Array<KeyQuestion & { written: boolean }>
    onStyle: (layout: KeyLayout) => void
    onOption: (name: KeyToggle, value: boolean) => void
    onInclude: (blockId: string) => void
    onEditAnswer: (blockId: string) => void
    /** A key pressed inside the printed key (the page's shortcuts never see it otherwise). */
    onKey?: (e: KeyboardEvent) => void
  } = $props()

  const STYLES: Array<{ value: KeyLayout; label: string; hint: string }> = [
    { value: 'compact', label: 'School key', hint: 'An answer grid for multiple choice, then short working with Ans:, as schools print it' },
    { value: 'full', label: 'Worked solutions', hint: 'Each question with its full solution' },
  ]

  interface Frame {
    id: number
    html: string
    ready: boolean
    /** What the paper's numbers and own questions were when this key was asked for: a click or
     *  a scroll on this key reads these, never the paper as it is now (it may have moved on). */
    numbers: number[]
    own: Array<KeyQuestion & { written: boolean }>
  }
  // The key on screen, and the next one while it loads (hidden until it has drawn).
  let frames = $state<Frame[]>([])
  let height = $state(0)
  let loading = $state(false)
  let error = $state('')
  let seq = 0
  let token = 0
  let shown: unknown = undefined // the revision the key on screen (or loading) was made from
  let wasActive = false
  let pendingScroll: { n: number; margin: number } | null = null
  let observer: ResizeObserver | null = null

  const visible = $derived(frames.find((f) => f.ready) ?? null)

  $effect(() => {
    const r = revision
    const on = active && !paused && !empty
    const delay = untrack(() => {
      const opened = on && !wasActive
      wasActive = on
      if (!on) pendingScroll = null // a scroll asked for on the way in no longer applies
      if (!on || r === shown) return null
      // straight away when the view opens; a moment after the last edit while it is open
      return opened ? 0 : KEY_REFRESH_MS
    })
    if (delay === null) return
    const t = setTimeout(() => void refresh(r), delay)
    return () => clearTimeout(t)
  })

  onDestroy(() => observer?.disconnect())

  async function refresh(r: unknown) {
    const mine = ++token
    shown = r
    loading = true
    error = ''
    // the paper this key is for: load() saves exactly this before it asks
    const asked = { numbers: [...numbers], own: own.map((q) => ({ ...q })) }
    try {
      const html = await load()
      if (mine !== token) return
      frames = [...frames.filter((f) => f.ready).slice(-1), { id: ++seq, html, ready: false, ...asked }]
    } catch (e) {
      if (mine !== token) return
      pendingScroll = null
      error = e instanceof Error ? e.message : String(e)
    } finally {
      if (mine === token) loading = false
    }
  }

  const retry = () => void refresh(revision)

  function measure(frame: HTMLIFrameElement) {
    const d = frame.contentDocument
    // the root's own box, not scrollHeight: that never drops below the frame's current height
    if (d?.documentElement) height = Math.ceil(d.documentElement.getBoundingClientRect().height)
  }

  function onLoad(f: Frame, e: Event) {
    // a key replaced before it finished loading must not take the screen from a newer one
    if (!frames.some((x) => x.id === f.id)) return
    const frame = e.currentTarget as HTMLIFrameElement
    measure(frame)
    frames = frames.filter((x) => x.id >= f.id).map((x) => (x.id === f.id ? { ...x, ready: true } : x))
    const d = frame.contentDocument
    const win = frame.contentWindow as (Window & typeof globalThis) | null
    if (!d) return
    // KaTeX and the fonts settle after load: follow the key's height as it does
    observer?.disconnect()
    if (win?.ResizeObserver) {
      observer = new win.ResizeObserver(() => measure(frame))
      observer.observe(d.documentElement)
    }
    d.addEventListener('keydown', (ev) => onKey(ev), true)
    // a press in the key closes the page's open menus, as a press anywhere else on the page does
    d.addEventListener('pointerdown', () => frame.dispatchEvent(new Event('pointerdown', { bubbles: true })))
    d.addEventListener('click', (ev) => {
      const n = keyRowNumber(ev.target as Element, f.numbers)
      const mine = f.own.find((q) => q.n === n)
      if (mine) onEditAnswer(mine.blockId)
    })
    // a teacher's own answers are written here: their rows open the answer on a click
    for (const q of f.own) {
      const row = findKeyRow(d, q.n, f.numbers)
      if (!row) continue
      const table = row.closest('table')
      // a worked solution, a grid column head, a label and its answer, or a whole table row
      const els = table?.classList.contains('key-pairs')
        ? [row, row.nextElementSibling]
        : table && !table.classList.contains('key-grid')
          ? [row.closest('tr')]
          : [row]
      for (const el of els) {
        if (!el || !('style' in el)) continue
        ;(el as HTMLElement).style.cursor = 'pointer'
        ;(el as HTMLElement).title = `Edit the answer to question ${q.n}`
      }
    }
    if (pendingScroll) {
      const { n, margin } = pendingScroll
      pendingScroll = null
      // once the page has grown to the new key's height
      void tick().then(() => scrollTo(frame, f, n, margin))
    }
  }

  let frameHost: HTMLElement | undefined = $state()

  /** Bring question `n`'s row to the top of the window, under a header `margin` px tall. True
   *  when the key on screen is up to date and has it. While a newer key is due or loading, the
   *  key on screen may number things differently: the scroll waits for the new key. */
  export function scrollToQuestion(n: number, margin = 0): boolean {
    pendingScroll = null
    const frame = frameHost?.querySelector<HTMLIFrameElement>('iframe.ready')
    if (!frame || !visible || loading || revision !== shown) {
      pendingScroll = { n, margin }
      return false
    }
    return scrollTo(frame, visible, n, margin)
  }

  function scrollTo(frame: HTMLIFrameElement, f: Frame, n: number, margin: number): boolean {
    const row = frame.contentDocument ? findKeyRow(frame.contentDocument, n, f.numbers) : null
    if (!row) return false
    const top = frame.getBoundingClientRect().top + row.getBoundingClientRect().top + window.scrollY
    window.scrollTo?.({ top: Math.max(0, top - margin - 16) })
    return true
  }

  const toggle = (name: KeyToggle) => (e: Event) => onOption(name, (e.currentTarget as HTMLInputElement).checked)
</script>

<section class="keyview" aria-label="Answer key" tabindex="-1">
  <div class="strip" role="group" aria-label="Answer key options">
    <div class="grp">
      <span class="lbl">Style</span>
      <div class="seg" role="radiogroup" aria-label="Answer key style">
        {#each STYLES as s (s.value)}
          <label class:on={options.layout === s.value} title={s.hint}>
            <input
              type="radio"
              name="key-style"
              value={s.value}
              checked={options.layout === s.value}
              onchange={() => onStyle(s.value)}
            />
            {s.label}
          </label>
        {/each}
      </div>
    </div>
    <div class="grp show">
      <span class="lbl">Show</span>
      {#if options.layout === 'full'}
        <label><input type="checkbox" checked={options.show_question} onchange={toggle('show_question')} /> The question</label>
      {/if}
      <label><input type="checkbox" checked={options.show_scheme} onchange={toggle('show_scheme')} /> Marking scheme (M1, A1)</label>
      {#if options.layout === 'compact'}
        <label><input type="checkbox" checked={options.show_marks} onchange={toggle('show_marks')} /> Marks</label>
        <label
          ><input type="checkbox" checked={options.one_mark_working} onchange={toggle('one_mark_working')} /> Working for
          1-mark questions</label
        >
      {/if}
    </div>
    <span class="state" aria-live="polite">
      {#if loading && visible}Updating…{/if}
    </span>
  </div>

  {#if leftOut.length || own.length}
    <div class="notes">
      {#if own.length}
        <p>
          <span class="lbl">Your answers</span>
          {#each own as q (q.blockId)}
            <button
              class="chip"
              aria-label="Edit the answer to question {q.n}{q.written ? '' : ' (not written yet)'}"
              onclick={() => onEditAnswer(q.blockId)}
              >Q{q.n}{#if !q.written}<span class="tag">to write</span>{/if}</button
            >
          {/each}
        </p>
      {/if}
      {#if leftOut.length}
        <p>
          <span class="lbl">Not in the key</span>
          {#each leftOut as q (q.blockId)}
            <span class="chip out"
              ><s>Q{q.n}</s><button aria-label="Include question {q.n} in the answer key" onclick={() => onInclude(q.blockId)}
                >Include</button
              ></span
            >
          {/each}
        </p>
      {/if}
    </div>
  {/if}

  {#if error}
    <p class="err" role="alert">
      <Icon name="alert" size={14} />
      <span>The answer key didn't {visible ? 'update' : 'load'}: {error}</span>
      <button class="retry" onclick={retry}>Try again</button>
    </p>
  {/if}

  {#if empty}
    <div class="sheet blank">
      <p>The paper has no questions yet. Add one and its answer shows here, as it will print.</p>
    </div>
  {:else}
    <div class="sheet" bind:this={frameHost}>
      {#if !visible && !error}
        <p class="loading" aria-busy="true">Loading the answer key…</p>
      {/if}
      <div class="frames" style:height={visible ? `${height}px` : undefined}>
        {#each frames as f (f.id)}
          <iframe
            class:ready={f.ready}
            title="Answer key, as it will print"
            srcdoc={f.html}
            inert={!f.ready}
            onload={(e) => onLoad(f, e)}
          ></iframe>
        {/each}
      </div>
    </div>
  {/if}
</section>

<style>
  .keyview {
    width: 210mm;
    max-width: 100%;
    margin: 0 auto;
    outline: none;
  }
  .strip {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--s3) var(--s6);
    margin: 0 0 var(--s3);
    padding: var(--s2) var(--s3);
    border: 1px solid var(--line);
    border-radius: var(--r-md);
    background: var(--page);
    font-size: 13px;
  }
  .grp {
    display: inline-flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px var(--s4);
  }
  .lbl {
    color: var(--ink-soft);
    margin-right: -6px;
  }
  .show label {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
  }
  .show input {
    margin: 0;
    accent-color: var(--verify);
  }
  /* the Settings page's two-way segmented control: radios styled as one pill */
  .seg {
    display: inline-flex;
    border: 1px solid var(--line);
    border-radius: var(--r-md);
    background: var(--wash);
    padding: 2px;
  }
  .seg label {
    position: relative;
    padding: 4px 10px;
    border-radius: var(--r-sm);
    color: var(--ink-soft);
    white-space: nowrap;
    cursor: pointer;
  }
  .seg label.on {
    background: var(--page);
    color: var(--ink);
    font-weight: 600;
    box-shadow: 0 0 0 1px var(--line);
  }
  .seg input {
    position: absolute;
    inset: 0;
    margin: 0;
    opacity: 0;
    cursor: pointer;
  }
  .seg label:has(input:focus-visible) {
    outline: 2px solid var(--verify);
    outline-offset: 1px;
  }
  .state {
    margin-left: auto;
    color: var(--ink-faint);
    font-size: 12px;
  }
  .notes {
    display: flex;
    flex-direction: column;
    gap: var(--s2);
    margin: 0 0 var(--s3);
    font-size: 13px;
  }
  .notes p {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    margin: 0;
  }
  .notes .lbl {
    margin-right: 4px;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 26px;
    padding: 0 var(--s2);
    border: 1px solid var(--line);
    border-radius: 999px;
    background: var(--page);
    color: var(--ink);
    font: inherit;
    font-size: 12.5px;
    font-weight: 600;
  }
  button.chip {
    cursor: pointer;
  }
  button.chip:hover {
    background: var(--wash);
  }
  .chip .tag {
    font-weight: 400;
    color: var(--mark);
  }
  .chip.out s {
    color: var(--ink-soft);
  }
  .chip.out button {
    padding: 0 0 0 6px;
    border: 0;
    border-left: 1px solid var(--line);
    background: none;
    color: var(--verify-ink);
    font: inherit;
    font-weight: 600;
    cursor: pointer;
  }
  .chip.out button:hover {
    text-decoration: underline;
  }
  .err {
    display: flex;
    align-items: center;
    gap: var(--s2);
    margin: 0 0 var(--s3);
    padding: var(--s2) var(--s3);
    border-radius: var(--r-md);
    background: var(--mark-soft);
    color: var(--mark);
    font-size: 13px;
  }
  .retry {
    margin-left: auto;
    height: 28px;
    padding: 0 var(--s3);
    border: 1px solid var(--line);
    border-radius: var(--r-sm);
    background: var(--page);
    color: var(--ink);
    font: inherit;
    font-weight: 600;
    cursor: pointer;
  }
  /* The sheet: an A4 page with the print margins, the printed key inside at the print width. */
  .sheet {
    position: relative;
    min-height: 120mm;
    padding: 18mm 16mm;
    background: var(--page);
    box-shadow: var(--shadow);
    box-sizing: border-box;
  }
  .sheet.blank p,
  .loading {
    margin: 0;
    color: var(--ink-faint);
    font-size: 14px;
  }
  .frames {
    position: relative;
  }
  iframe {
    display: block;
    width: 100%;
    height: 100%;
    border: 0;
  }
  /* the next key loads underneath, out of sight, and replaces the old one once drawn */
  iframe:not(.ready) {
    position: absolute;
    inset: 0;
    visibility: hidden;
  }
  @media (max-width: 599px) {
    .sheet {
      padding: var(--s4);
    }
  }
</style>
