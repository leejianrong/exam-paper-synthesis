<script lang="ts">
  // The right-hand inspector (EXA-93): status, provenance and metadata for the block you
  // are in, or a summary of the paper. Everything here is for the author; none of it prints.
  import type { DocNode } from './doc'
  import { describeBlock, summarise } from './inspector'

  export let blocks: DocNode[] = []
  export let marks = 0
  export let selectedId: string | null = null

  $: index = blocks.findIndex((b) => b.attrs?.block_id === selectedId)
  $: facts = index >= 0 ? describeBlock(blocks[index], index + 1) : null
  $: summary = summarise(blocks, marks)
</script>

<aside class="inspector" aria-label="Inspector">
  {#if facts}
    <h2>{facts.heading}</h2>
    <p class="status {facts.status.tone}">{facts.status.text}</p>
    <dl>
      {#each facts.rows as [label, value] (label)}
        <dt>{label}</dt>
        <dd>{value}</dd>
      {/each}
    </dl>
  {:else}
    <h2>This paper</h2>
    <dl>
      <dt>Questions</dt>
      <dd>{summary.questions}</dd>
      <dt>Total marks</dt>
      <dd>{summary.marks}</dd>
      {#if summary.generated}<dt>Generated</dt><dd>{summary.generated}</dd>{/if}
      {#if summary.bank}<dt>From my bank</dt><dd>{summary.bank}</dd>{/if}
      {#if summary.freeform}<dt>Free-form</dt><dd>{summary.freeform}</dd>{/if}
    </dl>
    <p class="hint">Click a question to see where it came from and how far it can be trusted.</p>
  {/if}
</aside>

<style>
  .inspector {
    width: 15rem;
    flex: 0 0 auto;
    position: sticky;
    top: 3.4rem;
    align-self: flex-start;
    background: var(--page);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 0.8rem 1rem;
    font-size: 13px;
    color: var(--ink);
  }
  h2 {
    margin: 0 0 0.5rem;
    font-size: 14px;
    font-weight: 600;
  }
  .status {
    margin: 0 0 0.7rem;
    padding: 0.35rem 0.5rem;
    border-radius: 6px;
    background: var(--wash);
    color: var(--ink-soft);
  }
  .status.ok {
    background: var(--verify-soft);
    color: var(--verify-ink);
  }
  .status.warn {
    background: var(--mark-soft);
    color: var(--mark);
  }
  dl {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.3rem 0.8rem;
    margin: 0;
  }
  dt {
    color: var(--ink-faint);
  }
  dd {
    margin: 0;
    overflow-wrap: anywhere;
  }
  .hint {
    color: var(--ink-faint);
    margin: 0.8rem 0 0;
  }
  @media (max-width: 1150px) {
    .inspector {
      position: static;
      width: 210mm;
      max-width: 100%;
      box-sizing: border-box;
      margin: 0 auto 0.6rem;
      order: -1;
    }
  }
</style>
