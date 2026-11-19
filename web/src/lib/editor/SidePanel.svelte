<script lang="ts" context="module">
  /** One section's line in the Marks group: its title and derived marks against its target. */
  export interface SectionRow {
    title: string
    marks: number
    target: number | null
  }
</script>

<script lang="ts">
  // The editor's right side panel (EXA-160, evolved from the EXA-93 inspector). "Paper" holds
  // what applies to the whole paper: marks per section, layout (time, first question number,
  // marks shown), the answer key options (a temporary home until S4 moves them to the key
  // view) and, on a generated paper, Regenerate unlocked. "Question" holds the inspector for
  // the block you are in; clicking into a question brings that tab forward.
  import { createEventDispatcher, tick } from 'svelte'
  import type { DocNode } from './doc'
  import Icon from '../Icon.svelte'
  import Inspector from './Inspector.svelte'
  import { summarise } from './inspector'
  import { paperSettings } from './paperSettings'
  import { DEFAULT_PLACEMENT } from './layout'

  export let blocks: DocNode[] = []
  export let marks = 0
  export let selectedId: string | null = null
  export let start = 1
  export let sections: SectionRow[] = []
  /** What "Regenerate unlocked" would do; null when the paper has nothing generated. */
  export let regen: { unlocked: number; locked: number } | null = null
  export let placeholdersLeft = 0
  export let busy = false
  export let tab: 'paper' | 'question' = 'paper'

  const dispatch = createEventDispatcher<{
    time: Event
    numberfrom: Event
    placement: Event
    regenerate: void
    remark: { blockId: string; remark: string }
    review: { blockId: string; reviewed: boolean }
  }>()

  $: index = blocks.findIndex((b) => b.attrs?.block_id === selectedId)
  $: questionLabel = index >= 0 ? `Question ${start + index}` : 'Question'
  $: summary = summarise(blocks, marks)

  // Selection decides what you see: entering a different question shows its tab.
  let shownFor: string | null = null
  $: showQuestion(index >= 0 ? selectedId : null)
  function showQuestion(id: string | null) {
    if (id !== null && id !== shownFor) tab = 'question'
    shownFor = id
  }

  let tabEls: Record<'paper' | 'question', HTMLButtonElement | undefined> = { paper: undefined, question: undefined }
  async function onTabKey(e: KeyboardEvent) {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) return
    e.preventDefault()
    tab = e.key === 'Home' ? 'paper' : e.key === 'End' ? 'question' : tab === 'paper' ? 'question' : 'paper'
    await tick()
    tabEls[tab]?.focus()
  }

  const pct = (s: SectionRow) => (s.target ? Math.min(100, Math.round((s.marks / s.target) * 100)) : 100)
  const off = (s: SectionRow) => s.target !== null && s.marks !== s.target
  const plural = (n: number, w: string) => `${n} ${w}${n === 1 ? '' : 's'}`
</script>

<aside class="panel" aria-label="Side panel">
  <div class="tabs" role="tablist" aria-label="Side panel">
    <button
      bind:this={tabEls.paper}
      role="tab"
      id="tab-paper"
      aria-controls="tabpanel-paper"
      aria-selected={tab === 'paper'}
      tabindex={tab === 'paper' ? 0 : -1}
      on:click={() => (tab = 'paper')}
      on:keydown={onTabKey}>Paper</button
    >
    <button
      bind:this={tabEls.question}
      role="tab"
      id="tab-question"
      aria-controls="tabpanel-question"
      aria-selected={tab === 'question'}
      tabindex={tab === 'question' ? 0 : -1}
      on:click={() => (tab = 'question')}
      on:keydown={onTabKey}>{questionLabel}</button
    >
  </div>

  <div class="pbody" role="tabpanel" id="tabpanel-paper" aria-labelledby="tab-paper" hidden={tab !== 'paper'}>
    <div class="pgroup">
      <h3>Marks</h3>
      {#each sections as s, i (i)}
        <div class="stat" class:off={off(s)}>
          <span>{s.title || `Section ${i + 1}`}</span>
          <span>
            {#if off(s)}<Icon name="alert" size={13} />{/if}
            {s.target === null ? `${s.marks}` : `${s.marks} / ${s.target}`}
            {#if off(s)}<span class="sr">{s.marks > (s.target ?? 0) ? 'over' : 'under'} target</span>{/if}
          </span>
        </div>
        {#if s.target !== null}
          <div class="bar" aria-hidden="true"><i class:off={off(s)} style:width="{pct(s)}%"></i></div>
        {/if}
      {/each}
      <div class="stat"><span>Total</span><span>{plural(marks, 'mark')}</span></div>
      <div class="stat"><span>Questions</span><span>{summary.questions}</span></div>
      {#if summary.questions}
        <p class="hint">
          {[
            summary.generated && `${summary.generated} generated`,
            summary.bank && `${summary.bank} from my bank`,
            summary.freeform && `${summary.freeform} my own`,
            summary.remarks && plural(summary.remarks, 'remark'),
          ]
            .filter(Boolean)
            .join(' · ')}
        </p>
      {/if}
    </div>

    <div class="pgroup">
      <h3>Layout</h3>
      <label class="field">
        <span>Time (minutes)</span>
        <input
          type="number"
          min="1"
          max="600"
          aria-label="Paper time in minutes"
          value={$paperSettings.time_min ?? ''}
          on:input={(e) => dispatch('time', e)}
        />
      </label>
      <label class="field">
        <span>First question number</span>
        <input
          type="number"
          min="1"
          max="999"
          placeholder="1"
          aria-label="First question number"
          value={$paperSettings.number_from ?? ''}
          on:input={(e) => dispatch('numberfrom', e)}
        />
      </label>
      <label class="field">
        <span>Marks shown</span>
        <select
          aria-label="Marks shown"
          value={$paperSettings.marks_placement ?? DEFAULT_PLACEMENT}
          on:change={(e) => dispatch('placement', e)}
        >
          <option value="answer">After the Ans: line</option>
          <option value="question">Beside the question</option>
          <option value="both">Both</option>
        </select>
      </label>
    </div>

    <div class="pgroup">
      <h3>Answer key</h3>
      <slot name="key" />
    </div>

    {#if regen || placeholdersLeft}
      <div class="pgroup">
        <h3>Generated paper</h3>
        {#if regen}
          <div class="stat">
            <span>Locked</span><span>{regen.locked} of {regen.locked + regen.unlocked}</span>
          </div>
        {/if}
        {#if placeholdersLeft}
          <div class="stat off">
            <span>To write</span>
            <span title="Generated placeholders still to write" data-testid="placeholders-left"
              >{placeholdersLeft} placeholder{placeholdersLeft === 1 ? '' : 's'} to write</span
            >
          </div>
        {/if}
        {#if regen}
          <button class="btn" disabled={busy || regen.unlocked === 0} on:click={() => dispatch('regenerate')}>
            <Icon name="swap" />Regenerate {regen.unlocked} unlocked…
          </button>
          <p class="hint">Locked questions and your own writing stay.</p>
        {/if}
      </div>
    {/if}
  </div>

  <div class="pbody" role="tabpanel" id="tabpanel-question" aria-labelledby="tab-question" hidden={tab !== 'question'}>
    <Inspector {blocks} {selectedId} {start} on:remark on:review />
  </div>
</aside>

<style>
  .panel {
    position: sticky;
    top: calc(var(--bar-h, 0px) + var(--s4));
    max-height: calc(100vh - var(--bar-h, 0px) - var(--s8));
    overflow-y: auto;
    background: var(--page);
    border: 1px solid var(--line);
    border-radius: var(--r-md);
    font-size: 13px;
    color: var(--ink);
  }
  .tabs {
    position: sticky;
    top: 0;
    z-index: 1;
    display: flex;
    background: var(--page);
    border-bottom: 1px solid var(--line);
  }
  [role='tab'] {
    flex: 1;
    min-width: 0;
    padding: 10px var(--s2);
    border: 0;
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
    background: none;
    font: inherit;
    font-weight: 500;
    color: var(--ink-soft);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    cursor: pointer;
  }
  [role='tab'][aria-selected='true'] {
    color: var(--ink);
    font-weight: 600;
    border-bottom-color: var(--verify);
  }
  .pbody {
    padding: var(--s4);
  }
  .pbody[hidden] {
    display: none;
  }
  .pgroup {
    margin-bottom: var(--s4);
  }
  .pgroup:last-child {
    margin-bottom: 0;
  }
  h3 {
    margin: 0 0 var(--s2);
    font-size: 12.5px;
    font-weight: 600;
    color: var(--ink-soft);
  }
  .stat {
    display: flex;
    justify-content: space-between;
    gap: var(--s2);
    padding: 3px 0;
  }
  .stat > span:first-child {
    color: var(--ink-soft);
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .stat > span:last-child {
    display: inline-flex;
    align-items: center;
    gap: var(--s1);
    white-space: nowrap;
  }
  .stat.off > span:last-child {
    color: var(--mark);
    font-weight: 600;
  }
  .bar {
    height: 4px;
    margin: 2px 0 var(--s2);
    border-radius: 2px;
    background: var(--line-soft);
  }
  .bar i {
    display: block;
    height: 100%;
    border-radius: 2px;
    background: var(--verify);
  }
  .bar i.off {
    background: var(--mark);
  }
  .field {
    display: grid;
    grid-template-columns: 1fr auto;
    align-items: center;
    gap: var(--s2);
    margin-bottom: var(--s2);
  }
  .field span {
    color: var(--ink-soft);
  }
  .field input,
  .field select {
    height: 30px;
    padding: 0 var(--s2);
    border: 1px solid var(--line);
    border-radius: var(--r-sm);
    background: var(--page);
    color: var(--ink);
    font: inherit;
  }
  .field input {
    width: 72px;
  }
  .field select {
    max-width: 160px;
  }
  /* the answer key controls arrive as they were in the top bar; lay them out as a stack here */
  .pgroup :global(.keyopts) {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: var(--s2);
    margin: 0;
    padding: 0;
    border: 0;
  }
  .pgroup :global(.keyopts legend) {
    display: none;
  }
  .pgroup :global(.keyopts select) {
    height: 30px;
    padding: 0 var(--s2);
    border: 1px solid var(--line);
    border-radius: var(--r-sm);
    background: var(--page);
    font: inherit;
  }
  .pgroup :global(.keyopts label) {
    display: flex;
    align-items: center;
    gap: var(--s2);
    color: var(--ink-soft);
  }
  .pgroup :global(.keyopts input[type='checkbox']) {
    accent-color: var(--verify);
    margin: 0;
  }
  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    width: 100%;
    height: 32px;
    margin-top: var(--s2);
    padding: 0 var(--s3);
    border: 1px solid var(--line);
    border-radius: var(--r-sm);
    background: var(--page);
    color: var(--ink);
    font: inherit;
    font-weight: 600;
    cursor: pointer;
  }
  .btn:hover:not(:disabled) {
    background: var(--wash);
  }
  .btn:disabled {
    opacity: 0.5;
    cursor: default;
  }
  .hint {
    margin: 6px 0 0;
    font-size: 12px;
    color: var(--ink-faint);
  }
  .sr {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
  }
  @media (max-width: 899px) {
    .panel {
      position: static;
      max-height: none;
    }
    .pbody:not([hidden]) {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: var(--s4) var(--s6);
    }
    .pgroup {
      margin: 0;
    }
  }
</style>
