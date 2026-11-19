<script lang="ts">
  // The inspector (EXA-93), the side panel's Question tab (EXA-160): status, provenance and
  // metadata for the block you are in. Everything here is for the author; none of it prints.
  import { createEventDispatcher } from 'svelte'
  import type { DocNode } from './doc'
  import { describeBlock } from './inspector'
  import ReviewControl from './ReviewControl.svelte'
  import type { Question } from '../types'

  export let blocks: DocNode[] = []
  export let selectedId: string | null = null
  /** The paper's first question number (EXA-134). */
  export let start = 1

  const dispatch = createEventDispatcher<{
    remark: { blockId: string; remark: string }
    review: { blockId: string; reviewed: boolean }
  }>()
  const MAX_REMARK = 2000

  $: index = blocks.findIndex((b) => b.attrs?.block_id === selectedId)
  $: facts = index >= 0 ? describeBlock(blocks[index], start + index) : null
  $: bankQuestion =
    index >= 0 && blocks[index].type === 'templatedQuestion' &&
    (blocks[index].attrs?.question as Question).source_type === 'sourced'
      ? (blocks[index].attrs?.question as Question)
      : null
  $: remark = index >= 0 ? String(blocks[index].attrs?.remark ?? '') : ''
</script>

<div class="inspector">
  {#if facts}
    <h2>{facts.heading}</h2>
    <p class="status {facts.status.tone}">{facts.status.text}</p>
    <dl>
      {#each facts.rows as [label, value] (label)}
        <dt>{label}</dt>
        <dd>{value}</dd>
      {/each}
    </dl>
    {#if bankQuestion}
      <ReviewControl
        id={bankQuestion.id}
        reviewed={Boolean(bankQuestion.validation.checks?.human_reviewed)}
        allowMissing
        on:changed={(e) => dispatch('review', { blockId: String(selectedId), reviewed: e.detail.reviewed })}
      />
    {/if}
    <label class="remark">
      <span>Remarks <small>(only you see these; never printed)</small></span>
      <textarea
        rows="4"
        maxlength={MAX_REMARK}
        placeholder="A note to yourself about this question"
        value={remark}
        on:input={(e) => dispatch('remark', { blockId: String(selectedId), remark: e.currentTarget.value })}
      ></textarea>
    </label>
  {:else}
    <p class="hint">Click a question to see where it came from and how far it can be trusted.</p>
  {/if}
</div>

<style>
  .inspector {
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
  .remark {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    margin-top: 0.8rem;
    color: var(--ink-soft);
  }
  .remark small {
    color: var(--ink-faint);
  }
  textarea {
    font: inherit;
    font-size: 13px;
    resize: vertical;
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 0.4rem 0.5rem;
    background: var(--paper);
    color: var(--ink);
  }
  .hint {
    color: var(--ink-faint);
    margin: 0;
  }
</style>
