<script lang="ts">
  // "Swap from your bank…" (EXA-33, R6.4): the owner's bank questions that fit this place (the
  // server's list: same marks and kind, not already in the paper, its topic first). Picking one
  // asks the server to put it there, as a bank question block.
  import { onMount } from 'svelte'
  import Dialog from '../Dialog.svelte'
  import ErrorNote from '../ErrorNote.svelte'
  import type { BankItem } from '../api'
  import { filterBank, needsReview, NO_FILTERS } from '../bank'
  import { canRetry, errorText } from '../errors'
  import { bankSwapOptions } from './docsApi'
  import FragmentView from './FragmentView.svelte'

  let {
    docId,
    blockId,
    onPick,
    onClose,
  }: { docId: string; blockId: string; onPick: (item: BankItem) => void; onClose: () => void } = $props()

  let items: BankItem[] = $state([])
  let loading = $state(true)
  let error = $state('')
  let retry: (() => void) | null = $state(null)
  let query = $state('')

  async function load() {
    loading = true
    error = ''
    try {
      items = await bankSwapOptions(docId, blockId)
    } catch (e) {
      error = errorText(e, "Couldn't load your question bank")
      retry = canRetry(e) ? () => void load() : null
    } finally {
      loading = false
    }
  }
  onMount(load)

  const shown = $derived(filterBank(items, { ...NO_FILTERS, query }))
  const marks = (item: BankItem) => item.question.question.total_marks
</script>

<Dialog title="Swap from your bank" width="40rem" {onClose}>
  {#if items.length > 3}
    <input class="search" type="search" placeholder="Search these questions" aria-label="Search bank questions" bind:value={query} />
  {/if}
  {#if error}<ErrorNote message={error} onRetry={retry} />{/if}
  {#if loading}
    <p class="hint">Loading your bank…</p>
  {:else if !error && items.length === 0}
    <p class="hint" data-testid="bank-swap-empty">
      Nothing in your bank fits here. A question needs the same marks as this one, the same kind of
      answer, and must not be in the paper already.
    </p>
  {:else if !error && shown.length === 0}
    <p class="hint">No bank questions match your search.</p>
  {/if}
  <ul class="list" aria-label="Bank questions that fit">
    {#each shown as item (item.id)}
      <li class="item" data-testid="bank-swap-item">
        <div class="tags">
          <span class="tag">{item.topic ?? 'No topic'}{item.level ? ` · ${item.level}` : ''}</span>
          <span class="tag">{marks(item)} mark{marks(item) === 1 ? '' : 's'}</span>
          {#if needsReview(item)}
            <span class="tag" class:warn={!item.reviewed}>{item.reviewed ? 'Reviewed' : 'Unreviewed'}</span>
          {:else}
            <span class="tag">Generated</span>
          {/if}
        </div>
        <FragmentView question={item.question} />
        <button
          class="use"
          type="button"
          aria-label={item.topic ? `Use this ${item.topic} question` : 'Use this question'}
          onclick={() => onPick(item)}>Use this</button
        >
      </li>
    {/each}
  </ul>
</Dialog>

<style>
  .search {
    width: 100%;
    box-sizing: border-box;
    margin-bottom: var(--s3);
    padding: 0.4rem 0.6rem;
    font: inherit;
    border: 1px solid var(--line);
    border-radius: var(--r-sm);
    background: var(--paper);
  }
  .hint {
    color: var(--ink-faint);
    margin: 0.5rem 0;
  }
  .list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 0.7rem;
  }
  .item {
    border: 1px solid var(--line);
    border-radius: var(--r-sm);
    padding: 0.7rem 0.8rem;
    background: var(--wash);
    display: grid;
    gap: 0.5rem;
  }
  .tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
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
  .use {
    justify-self: start;
    font: inherit;
    border: 1px solid var(--verify);
    background: var(--paper-2);
    color: var(--verify-ink);
    border-radius: var(--r-sm);
    padding: 0.35rem 0.9rem;
    cursor: pointer;
  }
</style>
