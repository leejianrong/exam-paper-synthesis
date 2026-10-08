<script lang="ts">
  // ADR-0019: review is a deliberate act. Marking a bank question reviewed asks you to confirm
  // you checked it (stem, answer, marking scheme); withdrawing a review is one click.
  import { createEventDispatcher } from 'svelte'
  import { setBankReviewed } from '../api'

  export let id: string
  export let reviewed = false
  /** In a paper the question may have left the bank; the paper's own copy can still be reviewed. */
  export let allowMissing = false

  const dispatch = createEventDispatcher<{ changed: { reviewed: boolean } }>()

  let confirming = false
  let checked = false
  let busy = false
  let error = ''

  async function apply(next: boolean) {
    busy = true
    error = ''
    try {
      const inBank = await setBankReviewed(id, next)
      if (!inBank && !allowMissing) {
        error = 'This question is no longer in your bank.'
        return
      }
      confirming = false
      checked = false
      dispatch('changed', { reviewed: next })
    } catch (e) {
      error = e instanceof Error ? e.message : String(e)
    } finally {
      busy = false
    }
  }
</script>

<div class="review">
  {#if reviewed}
    <button disabled={busy} on:click={() => apply(false)}>Withdraw review</button>
  {:else if !confirming}
    <button on:click={() => (confirming = true)}>Mark as reviewed…</button>
  {:else}
    <label class="check">
      <input type="checkbox" bind:checked />
      I have checked this question, its answer and its marking scheme.
    </label>
    <div class="row">
      <button class="go" disabled={!checked || busy} on:click={() => apply(true)}>Mark as reviewed</button>
      <button disabled={busy} on:click={() => ((confirming = false), (checked = false))}>Cancel</button>
    </div>
  {/if}
  {#if error}<p class="error" role="alert">{error}</p>{/if}
</div>

<style>
  .review {
    margin-top: 0.7rem;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    font-size: 12.5px;
  }
  .check {
    display: flex;
    gap: 0.4rem;
    align-items: flex-start;
    color: var(--ink-soft);
  }
  .row {
    display: flex;
    gap: 0.4rem;
  }
  button {
    font: inherit;
    font-size: 12.5px;
    border: 1px solid var(--line);
    background: var(--paper);
    color: var(--ink);
    border-radius: 6px;
    padding: 0.2rem 0.6rem;
    cursor: pointer;
    align-self: flex-start;
  }
  button:disabled {
    opacity: 0.5;
    cursor: default;
  }
  .go {
    border-color: var(--verify);
    color: var(--verify-ink);
  }
  .error {
    margin: 0;
    color: var(--mark);
  }
</style>
