<script lang="ts">
  // The "+" picker: choose how to add a question. Templated (generated) is live in W1;
  // "From my bank" arrives in W1d and "Free-form" in W2, so those tabs are shown disabled.
  import { createEventDispatcher } from 'svelte'
  import { generate } from '../api'
  import { TOPICS, DIFFICULTIES, blueprintCode } from '../topics'
  import type { Difficulty, Question } from '../types'
  import QuestionBody from './QuestionBody.svelte'

  const dispatch = createEventDispatcher<{ insert: { question: Question }; close: void }>()

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
      <button role="tab" aria-selected="true" class="tab on">Templated</button>
      <button role="tab" aria-selected="false" class="tab" disabled title="Coming soon"
        >From my bank</button
      >
      <button role="tab" aria-selected="false" class="tab" disabled title="Coming soon"
        >Free-form</button
      >
    </div>

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
          <QuestionBody {q} showStatus={false} />
          <button class="use" on:click={() => dispatch('insert', { question: q })}>Use this</button>
        </article>
      {/each}
      {#if !candidates.length && !loading && !error}
        <p class="hint">Pick a topic and difficulty, then generate a few options to choose from.</p>
      {/if}
    </div>
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
  .use {
    justify-self: start;
    background: var(--paper-2);
    color: var(--verify-ink);
  }
  .hint {
    color: var(--ink-faint);
    margin: 0.5rem 0;
  }
  .error {
    color: var(--mark);
  }
</style>
