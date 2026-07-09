<script>
  import { generate } from './lib/api.js'
  import QuestionCard from './lib/QuestionCard.svelte'

  let questions = []
  let loading = false
  let error = ''

  async function onGenerate() {
    loading = true
    error = ''
    try {
      const fresh = await generate('ratio_medium', 1)
      questions = [...fresh, ...questions]
    } catch (e) {
      error = e.message
    } finally {
      loading = false
    }
  }
</script>

<main>
  <h1>Exam Paper Synthesis</h1>

  <div class="panel">
    <p class="pinned">
      Topic <b>Ratio</b> · Difficulty <b>Medium</b>
      <span class="note">(pinned for V1 — selectors arrive in later slices)</span>
    </p>
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
      <QuestionCard {q} />
    {/each}
  </div>
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
  .pinned { margin: 0; color: var(--ink); }
  .note { color: var(--muted); font-size: 0.82rem; margin-left: 0.35rem; }
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
