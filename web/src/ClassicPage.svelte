<script lang="ts">
  import { generate, editQuestion, type EditOp } from './lib/api'
  import QuestionCard from './lib/QuestionCard.svelte'
  import WorksheetTray from './lib/WorksheetTray.svelte'
  import { worksheet } from './lib/worksheet'
  import type { Difficulty, Question } from './lib/types'
  import { TOPICS, DIFFICULTIES, blueprintCode } from './lib/topics'

  let questions: Question[] = []
  let loading = false
  let error = ''
  let busyId: string | null = null

  // Live selector state — default to Ratio / Medium (the old pinned V1 pair).
  let selectedPrefix = 'ratio'
  let selectedDifficulty: Difficulty = 'medium'
  $: selectedCode = blueprintCode(selectedPrefix, selectedDifficulty)

  const message = (e: unknown): string => (e instanceof Error ? e.message : String(e))
  const titleCase = (s: string): string => s.charAt(0).toUpperCase() + s.slice(1)

  async function onGenerate() {
    loading = true
    error = ''
    try {
      const fresh = await generate(selectedCode, 1)
      questions = [...fresh, ...questions]
    } catch (e) {
      error = message(e)
    } finally {
      loading = false
    }
  }

  async function onEdit(source: Question, op: EditOp) {
    busyId = source.id
    error = ''
    try {
      const child = await editQuestion(op, source)
      // Replace the source card in place — child.parent_id links back.
      questions = questions.map((x) => (x.id === source.id ? child : x))
    } catch (e) {
      error = message(e)
    } finally {
      busyId = null
    }
  }

  // Approve → add to the client-side worksheet (deduped by id in the store).
  function onApprove(q: Question) {
    worksheet.add(q)
  }

  // Discard → drop from the review list only (client-side, no server state).
  function onDiscard(id: string) {
    questions = questions.filter((q) => q.id !== id)
  }
</script>

<main>
  <div class="masthead">
    <svg class="glyph" viewBox="0 0 20 20" aria-hidden="true">
      <rect x="0" y="3" width="20" height="4" rx="1" />
      <rect x="0" y="8" width="13" height="4" rx="1" />
      <rect x="0" y="13" width="8" height="4" rx="1" />
    </svg>
    <span class="wordmark">exam-paper-synthesis</span>
  </div>

  <h1 class="title">Craft a question</h1>
  <p class="standfirst">
    Generate a fresh, validated P5&ndash;P6 question, nudge its difficulty, then approve it into a
    worksheet.
  </p>

  <div class="panel">
    <div class="selectors">
      <label class="field">
        <span>Topic</span>
        <select bind:value={selectedPrefix} aria-label="Topic">
          {#each TOPICS as topic (topic.prefix)}
            <option value={topic.prefix}>{topic.label}</option>
          {/each}
        </select>
      </label>
      <label class="field">
        <span>Difficulty</span>
        <select bind:value={selectedDifficulty} aria-label="Difficulty">
          {#each DIFFICULTIES as d (d)}
            <option value={d}>{titleCase(d)}</option>
          {/each}
        </select>
      </label>
    </div>
    <button class="generate" on:click={onGenerate} disabled={loading}>
      {loading ? 'Generating…' : 'Generate'}
    </button>
  </div>

  {#if error}
    <p class="error">{error}</p>
  {/if}

  {#if questions.length === 0 && !error}
    <p class="empty">Click <b>Generate</b> to create a fresh, validated question.</p>
  {/if}

  <div class="cards">
    {#each questions as q (q.id)}
      <QuestionCard
        {q}
        busy={busyId === q.id}
        added={$worksheet.items.some((item) => item.id === q.id)}
        on:edit={(e: CustomEvent<{ op: EditOp }>) => onEdit(q, e.detail.op)}
        on:approve={(e: CustomEvent<{ q: Question }>) => onApprove(e.detail.q)}
        on:discard={(e: CustomEvent<{ id: string }>) => onDiscard(e.detail.id)}
      />
    {/each}
  </div>

  <WorksheetTray />
</main>

<style>
  main {
    max-width: 760px;
    margin: 0 auto;
    padding: 2.5rem 1.35rem 4.5rem;
  }

  /* --- masthead (mono wordmark + unit-coloured glyph) --- */
  .masthead {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    margin-bottom: 1.75rem;
  }
  .glyph {
    width: 22px;
    height: 22px;
    flex: none;
  }
  .glyph rect:nth-child(1) {
    fill: var(--u1);
  }
  .glyph rect:nth-child(2) {
    fill: var(--u2);
  }
  .glyph rect:nth-child(3) {
    fill: var(--u3);
  }
  .wordmark {
    font-family: var(--mono);
    font-size: 13.5px;
    font-weight: 600;
    letter-spacing: -0.01em;
    color: var(--ink);
  }

  /* --- page title: serif = the trusted paper --- */
  .title {
    font-family: var(--serif);
    font-weight: 600;
    letter-spacing: -0.015em;
    font-size: clamp(1.7rem, 4vw, 2.3rem);
    line-height: 1.05;
    margin: 0 0 0.4rem;
    color: var(--ink);
    text-wrap: balance;
  }
  .standfirst {
    color: var(--ink-soft);
    font-size: 0.95rem;
    margin: 0 0 1.6rem;
    max-width: 54ch;
  }

  .panel {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
    background: var(--paper-2);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 0.95rem 1.1rem;
    margin-bottom: 1.4rem;
    box-shadow: var(--shadow);
  }
  .selectors {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
  }
  .field {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
  }
  /* uppercase micro-label = mono (engine data voice) */
  .field > span {
    font-family: var(--mono);
    color: var(--ink-faint);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }
  .field select {
    background: var(--paper);
    color: var(--ink);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 0.5rem 0.65rem;
    font-size: 0.9rem;
    font-family: var(--sans);
    cursor: pointer;
    min-width: 150px;
  }
  /* Generate = solid ink primary */
  .generate {
    background: var(--ink);
    color: var(--paper);
    border: 1px solid var(--ink);
    border-radius: 8px;
    padding: 0.62rem 1.35rem;
    font-size: 0.93rem;
    font-weight: 600;
    font-family: var(--sans);
    letter-spacing: -0.005em;
    cursor: pointer;
  }
  .generate:disabled {
    opacity: 0.6;
    cursor: default;
  }
  .error {
    color: var(--mark);
    background: var(--mark-soft);
    border: 1px solid color-mix(in srgb, var(--mark) 30%, transparent);
    padding: 0.75rem 1rem;
    border-radius: 8px;
  }
  .empty {
    color: var(--ink-soft);
  }
  .empty :global(b) {
    color: var(--ink);
    font-weight: 600;
  }
  .cards {
    display: flex;
    flex-direction: column;
    gap: 0.9rem;
  }
</style>
