<script lang="ts">
  // The chrome around a templated question inside the page: the question body plus a
  // toolbar of one-click edits (driven by the engine's available_ops), "Edit names",
  // move, add-below and delete. Every edit replaces the block's frozen snapshot with the
  // child object the API returns (lineage intact).
  import type { Readable } from 'svelte/store'
  import { editQuestion, setCosmetic, type EditOp } from '../api'
  import type { Question } from '../types'
  import NamesPopover from './NamesPopover.svelte'
  import QuestionBody from './QuestionBody.svelte'

  export let store: Readable<Question>
  export let ctx: {
    replace: (q: Question) => void
    remove: () => void
    move: (dir: -1 | 1) => void
    addBelow: () => void
  }

  $: q = $store
  $: part = q.question.parts[0]
  $: ops = q.available_ops ?? []
  const OP_LABELS: Array<[EditOp, string]> = [
    ['regenerate', 'Regenerate'],
    ['make-easier', 'Make easier'],
    ['make-harder', 'Make harder'],
    ['change-to-decimals', 'Change to decimals'],
    ['toggle-diagram', ''],
    ['toggle-bar-view', ''],
  ]
  $: barView =
    part.diagram?.type === 'bar_model_before_after' ? (part.diagram.view_mode ?? 'grouped') : null
  function opLabel(op: EditOp, fallback: string): string {
    if (op === 'toggle-diagram') return part.diagram ? 'Hide diagram' : 'Show diagram'
    if (op === 'toggle-bar-view') return barView === 'sliced' ? 'Group segments' : 'Slice into units'
    return fallback
  }

  let busy = false
  let error = ''
  let editingNames = false

  async function run(fn: () => Promise<Question>) {
    busy = true
    error = ''
    try {
      ctx.replace(await fn())
      editingNames = false
    } catch (e) {
      error = e instanceof Error ? e.message : String(e)
    } finally {
      busy = false
    }
  }
</script>

<div class="block" data-testid="question-block">
  <div class="num" aria-hidden="true"></div>
  <div class="main">
    <QuestionBody {q} />

    {#if editingNames}
      <NamesPopover
        {q}
        {busy}
        on:apply={(e) => run(() => setCosmetic(q, e.detail.changes))}
        on:close={() => (editingNames = false)}
      />
    {/if}

    {#if error}
      <p class="error" role="alert">{error}</p>
    {/if}

    <div class="toolbar" role="group" aria-label="question tools">
      {#each OP_LABELS as [op, fallback] (op)}
        {#if ops.includes(op)}
          <button disabled={busy} on:click={() => run(() => editQuestion(op, q))}
            >{opLabel(op, fallback)}</button
          >
        {/if}
      {/each}
      {#if q.source_type !== 'sourced' && q.blueprint_code}
        <button disabled={busy} on:click={() => (editingNames = !editingNames)}>Edit names</button>
      {/if}
      <span class="spacer"></span>
      <button title="Move up" aria-label="Move up" on:click={() => ctx.move(-1)}>↑</button>
      <button title="Move down" aria-label="Move down" on:click={() => ctx.move(1)}>↓</button>
      <button on:click={() => ctx.addBelow()}>+ Add below</button>
      <button class="danger" on:click={() => ctx.remove()}>Delete</button>
    </div>
  </div>
</div>

<style>
  .block {
    display: grid;
    grid-template-columns: 2rem 1fr;
    gap: 0.25rem;
    padding: 0.6rem 0.4rem;
    border: 1px solid transparent;
    border-radius: 8px;
  }
  .block:hover,
  .block:focus-within {
    border-color: var(--line);
    background: color-mix(in srgb, var(--paper-2) 60%, transparent);
  }
  .num::before {
    content: counter(q) '.';
    font-family: var(--mono);
    font-weight: 600;
    color: var(--ink-soft);
  }
  .toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
    margin-top: 0.4rem;
    opacity: 0;
    transition: opacity 0.12s;
  }
  .block:hover .toolbar,
  .block:focus-within .toolbar {
    opacity: 1;
  }
  .spacer {
    flex: 1;
  }
  button {
    font: inherit;
    font-family: var(--sans);
    font-size: 12px;
    border: 1px solid var(--line);
    background: var(--paper);
    color: var(--ink);
    border-radius: 6px;
    padding: 0.2rem 0.55rem;
    cursor: pointer;
  }
  button:hover:not(:disabled) {
    background: var(--paper-sink);
  }
  button:disabled {
    opacity: 0.5;
    cursor: default;
  }
  button.danger {
    color: var(--mark);
  }
  .error {
    color: var(--mark);
    font-size: 12.5px;
    margin: 0.3rem 0 0;
  }
</style>
