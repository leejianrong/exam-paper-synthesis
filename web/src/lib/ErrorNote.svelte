<script lang="ts">
  // A failure, said plainly (EXA-165), with Try again when the same request may work now. The
  // words come from errors.ts (`errorText`); the status and the server's detail are only in the
  // console. `strip` is the full-width bar under the editor's header.
  import Icon from './Icon.svelte'

  let {
    message,
    onRetry,
    retryLabel = 'Try again',
    busy = false,
    strip = false,
  }: {
    message: string
    onRetry?: (() => void) | null
    retryLabel?: string
    /** The retry is running: the button waits. */
    busy?: boolean
    strip?: boolean
  } = $props()
</script>

<p class="err" class:strip role="alert">
  <Icon name="alert" size={14} />
  <span class="text">{message}</span>
  {#if onRetry}
    <button class="retry" disabled={busy} onclick={() => onRetry?.()}>{busy ? 'Trying…' : retryLabel}</button>
  {/if}
</p>

<style>
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
  .err :global(svg) {
    flex: none;
  }
  .strip {
    margin: 0;
    border-radius: 0;
    padding: var(--s2) var(--s4);
  }
  .text {
    flex: 1;
    min-width: 0;
  }
  .retry {
    flex: none;
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
  .retry:hover:not(:disabled) {
    background: var(--wash);
  }
  .retry:disabled {
    color: var(--ink-faint);
    cursor: default;
  }
</style>
