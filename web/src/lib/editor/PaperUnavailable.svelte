<script lang="ts">
  // The page a paper that didn't open shows instead of the editor (EXA-165): what happened and
  // the way on. A missing paper (404) is not a fault, so it offers only the way back; a server
  // that can't be reached or failed offers Try again first.
  import { onMount } from 'svelte'
  import Icon from '../Icon.svelte'
  import { ApiError, canRetry, errorText } from '../errors'

  let { error, onRetry }: { error: unknown; onRetry: () => void } = $props()

  const status = $derived(error instanceof ApiError ? error.status : -1)
  const heading = $derived(
    status === 404
      ? "This paper doesn't exist or was deleted"
      : status === 403
        ? "You don't have access to this paper"
        : status === 0
          ? "Can't reach the server"
          : "This paper couldn't be opened",
  )
  const body = $derived(
    status === 404
      ? 'Check the link, or find the paper in Your papers.'
      : status === 403
        ? 'It belongs to another account. Sign in with the account that made it, or go back to Your papers.'
        : status === 0
          ? "The paper couldn't be opened. Check your internet connection, then try again."
          : errorText(error),
  )
  const retry = $derived(canRetry(error))

  let h1: HTMLElement | undefined = $state()
  onMount(() => h1?.focus())
</script>

<main class="state" data-testid="paper-unavailable">
  <div class="card">
    <span class="mark" aria-hidden="true"><Icon name={status === 404 ? 'cover' : 'alert'} size={20} /></span>
    <h1 bind:this={h1} tabindex="-1">{heading}</h1>
    <p>{body}</p>
    <div class="actions">
      {#if retry}
        <button class="primary" onclick={onRetry}>Try again</button>
        <a class="secondary" href="#/">Back to Your papers</a>
      {:else}
        <a class="primary" href="#/"><Icon name="back" /> Back to Your papers</a>
      {/if}
    </div>
  </div>
</main>

<style>
  .state {
    min-height: 100vh;
    background: var(--desk);
    padding: 18vh var(--s4) var(--s8);
    box-sizing: border-box;
  }
  .card {
    max-width: 460px;
    margin: 0 auto;
    padding: var(--s8);
    background: var(--page);
    border: 1px solid var(--line);
    border-radius: var(--r-md);
    box-shadow: var(--shadow);
  }
  .mark {
    display: inline-flex;
    color: var(--ink-faint);
  }
  h1 {
    margin: var(--s3) 0 var(--s2);
    font-size: 20px;
    line-height: 1.3;
  }
  h1:focus {
    outline: none;
  }
  p {
    margin: 0 0 var(--s6);
    color: var(--ink-soft);
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: var(--s3);
  }
  .primary,
  .secondary {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 32px;
    padding: 0 var(--s3);
    border-radius: var(--r-sm);
    font: inherit;
    font-size: 13.5px;
    font-weight: 600;
    text-decoration: none;
    cursor: pointer;
  }
  .primary {
    border: 1px solid var(--verify);
    background: var(--verify);
    color: var(--on-accent);
  }
  .primary:hover {
    background: var(--verify-ink);
  }
  .secondary {
    border: 1px solid var(--line);
    background: var(--page);
    color: var(--ink);
  }
  .secondary:hover {
    background: var(--wash);
  }
</style>
