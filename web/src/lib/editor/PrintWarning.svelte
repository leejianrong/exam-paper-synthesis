<script lang="ts">
  // EXA-137: the export refused a paper with generator placeholders nobody has written yet.
  // The teacher fills them (taken to the first one) or deliberately prints the paper as it is.
  import { createEventDispatcher } from 'svelte'

  /** The printed numbers of the empty questions (the API's 409 `questions`). */
  export let questions: number[]

  const dispatch = createEventDispatcher<{ fill: void; print: void; cancel: void }>()

  $: many = questions.length > 1
  $: listed =
    questions.length > 1
      ? `${questions.slice(0, -1).join(', ')} and ${questions[questions.length - 1]}`
      : String(questions[0] ?? '')
</script>

<div class="backdrop" role="presentation" on:click|self={() => dispatch('cancel')}>
  <div class="warn" role="alertdialog" aria-modal="true" aria-labelledby="pw-title" aria-describedby="pw-body">
    <h2 id="pw-title">{many ? `${questions.length} questions are` : 'A question is'} still empty</h2>
    <p id="pw-body">
      Question{many ? 's' : ''} <strong>{listed}</strong>
      {many ? 'were' : 'was'} left for you to write when the paper was generated.
      {many ? 'They would' : 'It would'} print as a blank gap.
    </p>
    <div class="row">
      <button class="go" on:click={() => dispatch('fill')}>Fill {many ? 'them' : 'it'}</button>
      <button on:click={() => dispatch('print')}>Print anyway</button>
      <button on:click={() => dispatch('cancel')}>Cancel</button>
    </div>
  </div>
</div>

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 60;
    display: grid;
    place-items: center;
    background: rgba(25, 28, 33, 0.5);
  }
  .warn {
    max-width: 26rem;
    padding: 1.1rem 1.25rem;
    background: var(--paper);
    color: var(--ink);
    border: 1px solid var(--line);
    border-radius: 8px;
    font-size: 13.5px;
  }
  h2 {
    margin: 0 0 0.5rem;
    font-size: 15px;
  }
  p {
    margin: 0 0 0.9rem;
    color: var(--ink-soft);
  }
  .row {
    display: flex;
    gap: 0.45rem;
  }
  button {
    font: inherit;
    border: 1px solid var(--line);
    background: var(--paper);
    color: var(--ink);
    border-radius: 6px;
    padding: 0.35rem 0.75rem;
    cursor: pointer;
  }
  .go {
    border-color: var(--verify);
    color: var(--verify-ink);
  }
</style>
