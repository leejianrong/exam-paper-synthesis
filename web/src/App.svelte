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
  <h1>Exam Paper Synthesis</h1>

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
    <button on:click={onGenerate} disabled={loading}>
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
    max-width: 720px;
    margin: 0 auto;
    padding: 2rem 1.25rem 4rem;
  }
  h1 {
    font-size: 1.4rem;
    margin: 0 0 1.25rem;
  }
  .panel {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 1rem 1.15rem;
    margin-bottom: 1.25rem;
  }
  .selectors {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
  }
  .field {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }
  .field > span {
    color: var(--muted);
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .field select {
    background: var(--card);
    color: var(--ink);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 0.45rem 0.6rem;
    font-size: 0.9rem;
    font-family: inherit;
    cursor: pointer;
  }
  button {
    background: var(--accent);
    color: #fff;
    border: 0;
    border-radius: 8px;
    padding: 0.6rem 1.25rem;
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
  }
  button:disabled { opacity: 0.6; cursor: default; }
  .error {
    color: var(--fail);
    background: var(--fail-bg);
    padding: 0.75rem 1rem;
    border-radius: 8px;
  }
  .empty { color: var(--muted); }
  .cards { display: flex; flex-direction: column; gap: 0.9rem; }
</style>
