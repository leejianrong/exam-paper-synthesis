<script lang="ts">
  // The question bank as its own page (EXA-167): every question the teacher imported, with
  // filters and a search, the review mark (ADR-0019, imported questions only) and Import. The
  // add-question picker's "From my bank" tab still lists the same bank inside a paper.
  import { onMount, tick } from 'svelte'
  import { listBank, type BankItem } from './api'
  import { filterBank, filterOptions, isFiltered, NO_FILTERS, needsReview, SOURCE_LABELS, type BankFilters } from './bank'
  import Dialog from './Dialog.svelte'
  import BankImport from './editor/BankImport.svelte'
  import FragmentView from './editor/FragmentView.svelte'
  import { withReviewed } from './editor/inspector'
  import ReviewControl from './editor/ReviewControl.svelte'
  import ErrorNote from './ErrorNote.svelte'
  import { canRetry, errorText } from './errors'
  import Icon from './Icon.svelte'

  /** Questions drawn at a time: each is drawn by the server, so a long bank grows on request. */
  const PAGE = 20

  let items = $state<BankItem[]>([])
  let loaded = $state(false)
  let loadError = $state<unknown>(null)
  let retrying = $state(false)
  let filters = $state<BankFilters>({ ...NO_FILTERS })
  let shownCount = $state(PAGE)
  let importing = $state(false)
  let announce = $state('')

  async function load(): Promise<void> {
    try {
      items = await listBank()
      loadError = null
    } catch (e) {
      // a failed reload after an import keeps the list on screen
      if (!loaded) loadError = e
      else announce = errorText(e, "Couldn't load your question bank")
    } finally {
      loaded = true
    }
  }

  async function retry(): Promise<void> {
    retrying = true
    loaded = false
    await load()
    retrying = false
  }

  onMount(load)

  const options = $derived(filterOptions(items))
  const shown = $derived(filterBank(items, filters))
  const filtered = $derived(isFiltered(filters))
  const visible = $derived(shown.slice(0, shownCount))
  const count = (n: number): string => `${n} ${n === 1 ? 'question' : 'questions'}`
  const summary = $derived(filtered ? `${shown.length} of ${count(items.length)}` : count(items.length))

  function setFilter<K extends keyof BankFilters>(key: K, value: BankFilters[K]): void {
    filters = { ...filters, [key]: value }
    shownCount = PAGE
  }

  function clearFilters(): void {
    filters = { ...NO_FILTERS }
    shownCount = PAGE
  }

  async function showMore(): Promise<void> {
    const at = shownCount
    shownCount += PAGE
    await tick()
    // keep the keyboard where the new questions start
    document.querySelectorAll<HTMLElement>('[data-testid="bank-question"]')[at]?.focus()
  }

  function onReviewed(id: string, reviewed: boolean): void {
    items = items.map((i) => (i.id === id ? { ...i, reviewed, question: withReviewed(i.question, reviewed) } : i))
  }

  function onImported(imported: number): void {
    announce = `${count(imported)} imported.`
    void load()
  }

  const titleCase = (s: string): string => s.charAt(0).toUpperCase() + s.slice(1)
  const meta = (i: BankItem): string =>
    [i.topic ?? 'No topic', i.level, i.difficulty && titleCase(i.difficulty)].filter(Boolean).join(' · ')
  const origin = (i: BankItem): string => {
    const s = (i.question as { source?: { origin?: string; year?: number } }).source
    return [s?.origin, s?.year].filter(Boolean).join(', ')
  }
</script>

<main>
  <div class="head">
    <h1>Question bank</h1>
    <button class="primary" aria-haspopup="dialog" onclick={() => (importing = true)}>
      <Icon name="upload" />Import questions from a file
    </button>
  </div>
  <p class="lede">
    Questions you've imported, ready to add to any paper with <b>Add question › From my bank</b>. They
    start unreviewed: mark each one reviewed once you've checked it.
  </p>

  <p class="visually-hidden" role="status">{announce}</p>

  {#if !loaded}
    <div role="status" data-testid="bank-skeleton">
      <span class="visually-hidden">Loading your question bank…</span>
      <ul class="list" aria-hidden="true">
        {#each [70, 52, 64] as w, i (i)}
          <li class="card">
            <span class="skel" style:width="9rem" style:height="10px"></span>
            <span class="skel" style:width="{w}%" style:height="14px"></span>
            <span class="skel" style:width="{w - 20}%" style:height="14px"></span>
          </li>
        {/each}
      </ul>
    </div>
  {:else if loadError}
    <ErrorNote
      message={errorText(loadError, "Couldn't load your question bank")}
      onRetry={canRetry(loadError) ? () => void retry() : null}
      busy={retrying}
    />
  {:else if items.length === 0}
    <div class="empty">
      <p><b>Your bank is empty.</b></p>
      <p>
        Import questions from a file (.json) to keep them here. Each one can then go into any paper, and
        you can mark it reviewed once you've checked it.
      </p>
    </div>
  {:else}
    <div class="filters" role="search" aria-label="Filter questions">
      <label class="search">
        <Icon name="search" />
        <input
          type="search"
          value={filters.query}
          oninput={(e) => setFilter('query', e.currentTarget.value)}
          onkeydown={(e) => {
            if (e.key === 'Escape' && filters.query) {
              e.preventDefault()
              setFilter('query', '')
            }
          }}
          placeholder="Search questions"
          aria-label="Search questions"
        />
      </label>
      <select aria-label="Topic" value={filters.topic} onchange={(e) => setFilter('topic', e.currentTarget.value)}>
        <option value="">All topics</option>
        {#each options.topics as t (t)}<option value={t}>{t}</option>{/each}
      </select>
      <select aria-label="Level" value={filters.level} onchange={(e) => setFilter('level', e.currentTarget.value)}>
        <option value="">All levels</option>
        {#each options.levels as l (l)}<option value={l}>{l}</option>{/each}
      </select>
      <select
        aria-label="Difficulty"
        value={filters.difficulty}
        onchange={(e) => setFilter('difficulty', e.currentTarget.value)}
      >
        <option value="">Any difficulty</option>
        {#each options.difficulties as d (d)}<option value={d}>{titleCase(d)}</option>{/each}
      </select>
      <select aria-label="Source" value={filters.source} onchange={(e) => setFilter('source', e.currentTarget.value)}>
        <option value="">Imported and generated</option>
        {#each options.sources as s (s)}<option value={s}>{SOURCE_LABELS[s] ?? s}</option>{/each}
      </select>
      <select
        aria-label="Review"
        value={filters.review}
        onchange={(e) => setFilter('review', e.currentTarget.value as BankFilters['review'])}
      >
        <option value="">Reviewed or not</option>
        <option value="reviewed">Reviewed</option>
        <option value="unreviewed">Not reviewed</option>
      </select>
    </div>

    <div class="count">
      <span data-testid="bank-count">{summary}</span>
      {#if filtered}<button class="quiet" onclick={clearFilters}>Clear filters</button>{/if}
    </div>

    {#if shown.length === 0}
      <p class="none">No questions match these filters.</p>
    {:else}
      <ul class="list" aria-label="Questions in your bank">
        {#each visible as item (item.id)}
          <li class="card" data-testid="bank-question" tabindex="-1">
            <div class="line">
              <span class="meta">{meta(item)}</span>
              {#if needsReview(item)}
                <span class="chip" class:ok={item.reviewed}>
                  {#if item.reviewed}<Icon name="check" size={12} />{/if}{item.reviewed ? 'Reviewed' : 'Unreviewed'}
                </span>
              {:else}
                <span class="chip ok">{SOURCE_LABELS[item.source_type] ?? item.source_type}</span>
              {/if}
            </div>
            {#if origin(item)}<p class="origin">{origin(item)}</p>{/if}
            <FragmentView question={item.question} />
            {#if needsReview(item)}
              <ReviewControl
                id={item.id}
                reviewed={item.reviewed}
                on:changed={(e: CustomEvent<{ reviewed: boolean }>) => onReviewed(item.id, e.detail.reviewed)}
              />
            {/if}
          </li>
        {/each}
      </ul>
      {#if shown.length > visible.length}
        <button class="more" onclick={() => void showMore()}>
          Show more ({shown.length - visible.length} left)
        </button>
      {/if}
    {/if}
  {/if}
</main>

{#if importing}
  <Dialog title="Import questions from a file" width="38rem" onClose={() => (importing = false)}>
    <BankImport
      on:done={(e: CustomEvent<{ imported: number }>) => onImported(e.detail.imported)}
      on:cancel={() => (importing = false)}
    />
  </Dialog>
{/if}

<style>
  main {
    max-width: 760px;
    margin: 0 auto;
    padding: var(--s8) var(--s4) 4.5rem;
  }
  .head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--s3);
    margin-bottom: var(--s2);
  }
  h1 {
    flex: 1;
    margin: 0;
    font-size: 24px;
  }
  @media (max-width: 600px) {
    /* the title keeps its line; Import goes under it */
    h1 {
      flex-basis: 100%;
    }
  }
  .lede {
    margin: 0 0 var(--s4);
    color: var(--ink-soft);
    font-size: 13.5px;
    max-width: 60ch;
  }
  .primary {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 32px;
    padding: 0 var(--s3);
    border: 1px solid var(--verify);
    border-radius: var(--r-sm);
    background: var(--verify);
    color: var(--on-accent);
    font: inherit;
    font-size: 13.5px;
    font-weight: 600;
    cursor: pointer;
  }
  .primary:hover {
    background: var(--verify-ink);
  }
  .filters {
    display: flex;
    flex-wrap: wrap;
    gap: var(--s2);
    margin-bottom: var(--s3);
  }
  .search {
    display: flex;
    align-items: center;
    gap: 6px;
    flex: 1 1 200px;
    height: 32px;
    box-sizing: border-box;
    padding: 0 10px;
    border: 1px solid var(--line);
    border-radius: var(--r-sm);
    background: var(--page);
    color: var(--ink-faint);
  }
  .search:focus-within {
    outline: 2px solid var(--verify);
    outline-offset: 1px;
  }
  .search input {
    flex: 1;
    min-width: 0;
    border: 0;
    outline: 0;
    background: none;
    font: inherit;
    font-size: 13px;
    color: var(--ink);
  }
  select {
    height: 32px;
    max-width: 100%;
    padding: 0 var(--s2);
    border: 1px solid var(--line);
    border-radius: var(--r-sm);
    background: var(--page);
    color: var(--ink);
    font: inherit;
    font-size: 13px;
  }
  .count {
    display: flex;
    align-items: center;
    gap: var(--s3);
    min-height: 28px;
    margin-bottom: var(--s2);
    color: var(--ink-faint);
    font-size: 12.5px;
  }
  .quiet {
    height: 28px;
    padding: 0 var(--s2);
    border: 0;
    border-radius: var(--r-sm);
    background: none;
    color: var(--verify-ink);
    font: inherit;
    font-size: 12.5px;
    font-weight: 600;
    cursor: pointer;
  }
  .quiet:hover {
    background: var(--wash);
  }
  .list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: var(--s3);
  }
  .card {
    display: grid;
    gap: var(--s2);
    min-width: 0;
    padding: var(--s3) var(--s4);
    border: 1px solid var(--line);
    border-radius: var(--r-md);
    background: var(--page);
  }
  .card :global(.fragment) {
    min-width: 0;
    overflow-x: auto;
  }
  .line {
    display: flex;
    align-items: center;
    gap: var(--s2);
    flex-wrap: wrap;
  }
  .meta {
    flex: 1;
    color: var(--ink-soft);
    font-size: 12.5px;
    font-weight: 600;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 0 var(--s2);
    border: 1px solid var(--line);
    border-radius: 999px;
    background: var(--wash);
    color: var(--ink-soft);
    font-size: 11.5px;
    font-weight: 600;
    line-height: 20px;
  }
  .chip:not(.ok)::before {
    content: '';
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--u2);
  }
  .chip.ok {
    border-color: transparent;
    background: var(--verify-soft);
    color: var(--verify-ink);
  }
  .origin {
    margin: 0;
    color: var(--ink-faint);
    font-size: 12px;
  }
  .card :global(.review) {
    margin-top: 0;
  }
  .empty,
  .none {
    color: var(--ink-soft);
    font-size: 13.5px;
  }
  .empty {
    padding: var(--s6);
    border: 1px dashed var(--line);
    border-radius: var(--r-md);
    background: var(--page);
  }
  .empty p {
    margin: 0 0 var(--s2);
    max-width: 52ch;
  }
  .empty p:last-child {
    margin: 0;
  }
  .more {
    margin-top: var(--s3);
    height: 32px;
    padding: 0 var(--s3);
    border: 1px solid var(--line);
    border-radius: var(--r-sm);
    background: var(--page);
    color: var(--ink);
    font: inherit;
    font-size: 13px;
    cursor: pointer;
  }
  .more:hover {
    background: var(--wash);
  }
</style>
