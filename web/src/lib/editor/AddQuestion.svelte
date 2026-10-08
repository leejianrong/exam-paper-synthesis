<script lang="ts">
  // The "+" picker: choose how to add a question. Templated (generated), From my bank, or
  // Free-form (an empty teacher-written block, inserted straight away).
  import { createEventDispatcher } from 'svelte'
  import { generate, listBank, type BankItem } from '../api'
  import ReviewControl from './ReviewControl.svelte'
  import { withReviewed } from './inspector'
  import { TOPICS, DIFFICULTIES, blueprintCode } from '../topics'
  import type { Difficulty, Question } from '../types'
  import BankImport from './BankImport.svelte'
  import FragmentView from './FragmentView.svelte'
  import QuestionBody from './QuestionBody.svelte'

  const dispatch = createEventDispatcher<{ insert: { question: Question }; freeform: void; close: void }>()

  type Tab = 'templated' | 'bank'
  let tab: Tab = 'templated'

  let prefix = 'ratio'
  let difficulty: Difficulty = 'medium'
  let candidates: Question[] = []
  let loading = false
  let error = ''

  const titleCase = (s: string): string => s.charAt(0).toUpperCase() + s.slice(1)

  async function onGenerate() {
    loading = true
    error = ''
    try {
      candidates = await generate(blueprintCode(prefix, difficulty), 3)
    } catch (e) {
      error = e instanceof Error ? e.message : String(e)
    } finally {
      loading = false
    }
  }

  // --- From my bank -----------------------------------------------------------------
  let bankItems: BankItem[] = []
  let bankLoaded = false
  let bankLoading = false
  let bankError = ''
  let bankTopic = ''
  let reviewedOnly = false
  let importing = false

  async function afterImport() {
    bankLoaded = false // pick up what was just imported
    bankItems = []
    bankLoading = false
    try {
      bankItems = await listBank()
      bankLoaded = true
    } catch (e) {
      bankError = e instanceof Error ? e.message : String(e)
    }
  }

  async function showBank() {
    tab = 'bank'
    if (bankLoaded || bankLoading) return
    bankLoading = true
    bankError = ''
    try {
      bankItems = await listBank()
      bankLoaded = true
    } catch (e) {
      bankError = e instanceof Error ? e.message : String(e)
    } finally {
      bankLoading = false
    }
  }

  // The review flag travels with the snapshot a paper takes, so keep the listed copy in step.
  function onReviewed(id: string, reviewed: boolean) {
    bankItems = bankItems.map((i) =>
      i.id === id ? { ...i, reviewed, question: withReviewed(i.question, reviewed) } : i,
    )
  }

  $: bankTopics = [...new Set(bankItems.map((i) => i.topic).filter((t): t is string => !!t))].sort()
  $: shownBank = bankItems.filter(
    (i) => (!bankTopic || i.topic === bankTopic) && (!reviewedOnly || i.reviewed),
  )

  function onKey(e: KeyboardEvent) {
    if (e.key === 'Escape') dispatch('close')
  }
</script>

<svelte:window on:keydown={onKey} />

<div class="backdrop" role="presentation" on:click|self={() => dispatch('close')}>
  <div class="dialog" role="dialog" aria-modal="true" aria-label="Add question">
    <header>
      <h2>Add a question</h2>
      <button class="x" aria-label="Close" on:click={() => dispatch('close')}>×</button>
    </header>

    <div class="tabs" role="tablist">
      <button
        role="tab"
        aria-selected={tab === 'templated'}
        class="tab"
        class:on={tab === 'templated'}
        on:click={() => (tab = 'templated')}>Templated</button
      >
      <button
        role="tab"
        aria-selected={tab === 'bank'}
        class="tab"
        class:on={tab === 'bank'}
        on:click={showBank}>From my bank</button
      >
      <button
        role="tab"
        aria-selected="false"
        class="tab"
        title="Type your own question on the page"
        on:click={() => dispatch('freeform')}>Free-form</button
      >
    </div>

    {#if tab === 'templated'}
    <div class="selectors">
      <label
        ><span>Topic</span>
        <select bind:value={prefix} aria-label="Topic">
          {#each TOPICS as t (t.prefix)}<option value={t.prefix}>{t.label}</option>{/each}
        </select>
      </label>
      <label
        ><span>Difficulty</span>
        <select bind:value={difficulty} aria-label="Difficulty">
          {#each DIFFICULTIES as d (d)}<option value={d}>{titleCase(d)}</option>{/each}
        </select>
      </label>
      <button class="go" on:click={onGenerate} disabled={loading}>
        {loading ? 'Generating…' : candidates.length ? 'Generate more' : 'Generate'}
      </button>
    </div>

    {#if error}<p class="error" role="alert">{error}</p>{/if}

    <div class="candidates">
      {#each candidates as q (q.id)}
        <article class="candidate" data-testid="candidate">
          <QuestionBody {q} />
          <button class="use" on:click={() => dispatch('insert', { question: q })}>Use this</button>
        </article>
      {/each}
      {#if !candidates.length && !loading && !error}
        <p class="hint">Pick a topic and difficulty, then generate a few options to choose from.</p>
      {/if}
    </div>
    {:else if importing}
      <BankImport
        on:done={afterImport}
        on:cancel={() => (importing = false)}
      />
    {:else}
      <div class="selectors">
        <label
          ><span>Topic</span>
          <select bind:value={bankTopic} aria-label="Bank topic">
            <option value="">All topics</option>
            {#each bankTopics as t (t)}<option value={t}>{t}</option>{/each}
          </select>
        </label>
        <label class="check"
          ><input type="checkbox" bind:checked={reviewedOnly} /> Reviewed only</label
        >
        <button class="import-btn" on:click={() => (importing = true)}>Import…</button>
      </div>

      {#if bankError}<p class="error" role="alert">{bankError}</p>{/if}
      {#if bankLoading}<p class="hint">Loading your bank…</p>{/if}

      <div class="candidates">
        {#each shownBank as item (item.id)}
          <article class="candidate" data-testid="bank-item">
            <div class="origin">
              <span class="tag">{item.topic ?? 'Untopiced'}{item.level ? ` · ${item.level}` : ''}</span>
              <span class="tag" class:warn={!item.reviewed}
                >{item.reviewed ? 'Reviewed' : 'Unreviewed'}</span
              >
            </div>
            <FragmentView question={item.question} />
            {#if item.source_type === 'sourced'}
              <ReviewControl
                id={item.id}
                reviewed={item.reviewed}
                on:changed={(e) => onReviewed(item.id, e.detail.reviewed)}
              />
            {/if}
            <button class="use" on:click={() => dispatch('insert', { question: item.question })}
              >Use this</button
            >
          </article>
        {/each}
        {#if bankLoaded && bankItems.length === 0}
          <p class="hint">
            Nothing in your bank yet. Use <b>Import…</b> to add question JSON files (or run
            <code>mathgen bank import &lt;file.json&gt;</code>) and they will show up here.
          </p>
        {:else if bankLoaded && shownBank.length === 0}
          <p class="hint">No bank questions match these filters.</p>
        {/if}
      </div>
    {/if}
  </div>
</div>

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba(25, 28, 33, 0.45);
    display: grid;
    place-items: center;
    z-index: 50;
    padding: 1rem;
  }
  .dialog {
    background: var(--paper-2);
    border: 1px solid var(--line);
    border-radius: 12px;
    box-shadow: var(--shadow);
    width: min(720px, 100%);
    max-height: 90vh;
    overflow: auto;
    padding: 1rem 1.2rem 1.2rem;
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  h2 {
    margin: 0;
    font-family: var(--serif);
    font-size: 1.3rem;
  }
  .x {
    border: none;
    background: none;
    font-size: 1.5rem;
    cursor: pointer;
    color: var(--ink-soft);
  }
  .tabs {
    display: flex;
    gap: 0.3rem;
    margin: 0.7rem 0;
    border-bottom: 1px solid var(--line);
  }
  .tab {
    border: none;
    background: none;
    padding: 0.4rem 0.8rem;
    font: inherit;
    color: var(--ink-faint);
  }
  .tab.on {
    color: var(--ink);
    border-bottom: 2px solid var(--verify);
  }
  .tab:disabled {
    cursor: not-allowed;
  }
  .selectors {
    display: flex;
    flex-wrap: wrap;
    gap: 0.7rem;
    align-items: end;
    margin-bottom: 0.8rem;
  }
  label {
    display: grid;
    gap: 0.2rem;
    font-size: 12px;
    color: var(--ink-soft);
  }
  select {
    font: inherit;
    padding: 0.35rem 0.5rem;
    border: 1px solid var(--line);
    border-radius: 6px;
    background: var(--paper);
  }
  .go,
  .use {
    font: inherit;
    border: 1px solid var(--verify);
    background: var(--verify);
    color: #fff;
    border-radius: 6px;
    padding: 0.4rem 0.9rem;
    cursor: pointer;
  }
  .go:disabled {
    opacity: 0.6;
  }
  .candidates {
    display: grid;
    gap: 0.7rem;
  }
  .candidate {
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 0.7rem 0.8rem;
    background: var(--wash);
    display: grid;
    gap: 0.5rem;
  }
  .import-btn {
    font: inherit;
    margin-left: auto;
    border: 1px solid var(--line);
    background: var(--paper);
    color: var(--ink);
    border-radius: 6px;
    padding: 0.35rem 0.8rem;
    cursor: pointer;
  }
  .use {
    justify-self: start;
    background: var(--paper-2);
    color: var(--verify-ink);
  }
  .hint {
    color: var(--ink-faint);
    margin: 0.5rem 0;
  }
  .check {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 0.4rem;
    font-size: 13px;
    padding-bottom: 0.4rem;
  }
  .origin {
    display: flex;
    gap: 0.4rem;
    font-family: var(--mono);
    font-size: 11.5px;
  }
  .tag {
    padding: 0.1rem 0.5rem;
    border-radius: 999px;
    background: var(--page);
    border: 1px solid var(--line);
    color: var(--ink-soft);
  }
  .tag.warn {
    background: var(--mark-soft);
    border-color: transparent;
    color: var(--mark);
  }
  code {
    font-family: var(--mono);
    font-size: 12px;
    background: var(--wash);
    padding: 0.05rem 0.3rem;
    border-radius: 4px;
  }
  .error {
    color: var(--mark);
  }
</style>
