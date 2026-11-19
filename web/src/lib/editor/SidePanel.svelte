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
  // marks shown) and, on a generated paper, Regenerate unlocked. The answer key options sit
  // above the key itself, in the key view (EXA-162). The second tab follows the selection: the
  // inspector for the question you are in, or the settings of a selected section or the cover
  // (EXA-164); selecting a different one brings that tab forward.
  import { createEventDispatcher, tick } from 'svelte'
  import type { DocNode } from './doc'
  import Icon from '../Icon.svelte'
  import Inspector from './Inspector.svelte'
  import { summarise } from './inspector'
  import { paperSettings } from './paperSettings'
  import { paperPlacement } from './layout'
  import { outline } from './sections'
  import type { SettingsBlock } from './blockSettings'
  import MarksShown from './MarksShown.svelte'
  import SectionSettings from './SectionSettings.svelte'
  import CoverSettings from './CoverSettings.svelte'

  export let blocks: DocNode[] = []
  export let marks = 0
  export let selectedId: string | null = null
  export let start = 1
  export let sections: SectionRow[] = []
  /** What "Regenerate unlocked" would do; null when the paper has nothing generated. */
  export let regen: { unlocked: number; locked: number } | null = null
  export let placeholdersLeft = 0
  export let busy = false
  export let tab: 'paper' | 'selection' = 'paper'
  /** A selected section or the cover: its settings show instead of a question's (EXA-164). */
  export let context: SettingsBlock | null = null
  /** Bumps each time the author selects a section or the cover (not when one moves because a
   *  block above it came or went), so only a real selection brings its tab forward. */
  export let pick = 0
  /** A swap or regenerate is running: the section and cover settings wait (EXA-164). */
  export let locked = false

  const dispatch = createEventDispatcher<{
    time: Event
    numberfrom: Event
    placement: Event
    regenerate: void
    remark: { blockId: string; remark: string }
    review: { blockId: string; reviewed: boolean }
    blockattrs: Record<string, unknown>
    done: void
  }>()

  $: index = blocks.findIndex((b) => b.attrs?.block_id === selectedId)
  $: selectionLabel = !context
    ? index >= 0
      ? `Question ${start + index}`
      : 'Question'
    : context.kind === 'cover'
      ? 'Cover page'
      : String(context.attrs.title ?? '').trim() || `Section ${context.index + 1}`
  $: summary = summarise(blocks, marks)

  // Selection decides what you see: selecting a different question, section or the cover shows
  // its tab.
  let shownFor: string | null = null
  $: showSelection(
    context
      ? `${context.kind}#${pick}`
      : index >= 0
        ? `q:${selectedId}`
        : null,
  )
  function showSelection(key: string | null) {
    if (key !== null && key !== shownFor) tab = 'selection'
    shownFor = key
  }

  let tabEls: Record<'paper' | 'selection', HTMLButtonElement | undefined> = { paper: undefined, selection: undefined }
  async function onTabKey(e: KeyboardEvent) {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) return
    e.preventDefault()
    tab = e.key === 'Home' ? 'paper' : e.key === 'End' ? 'selection' : tab === 'paper' ? 'selection' : 'paper'
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
      bind:this={tabEls.selection}
      role="tab"
      id="tab-selection"
      aria-controls="tabpanel-selection"
      aria-selected={tab === 'selection'}
      tabindex={tab === 'selection' ? 0 : -1}
      on:click={() => (tab = 'selection')}
      on:keydown={onTabKey}>{selectionLabel}</button
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
        <MarksShown value={paperPlacement($paperSettings)} on:change={(e) => dispatch('placement', e)} />
      </label>
      <p class="hint">
        Sections follow this unless they set their own; multiple-choice and short-answer sections show
        marks in the section header.
      </p>
    </div>

    {#if regen || placeholdersLeft}
      <div class="pgroup">
        <h3 id="panel-generated" tabindex="-1">Generated paper</h3>
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

  <div class="pbody" role="tabpanel" id="tabpanel-selection" aria-labelledby="tab-selection" hidden={tab !== 'selection'}>
    {#if context?.kind === 'section'}
      <SectionSettings
        attrs={context.attrs}
        info={$outline[context.index]}
        paper={paperPlacement($paperSettings)}
        disabled={locked}
        on:change={(e) => dispatch('blockattrs', e.detail)}
        on:done
      />
    {:else if context?.kind === 'cover'}
      <CoverSettings
        attrs={context.attrs}
        disabled={locked}
        on:change={(e) => dispatch('blockattrs', e.detail)}
        on:done
      />
    {:else}
      <Inspector {blocks} {selectedId} {start} on:remark on:review />
    {/if}
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
  h3:focus {
    outline: none;
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
  .field :global(select) {
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
  .field :global(select) {
    max-width: 160px;
  }
  .field + .hint {
    margin: calc(-1 * var(--s1)) 0 var(--s2);
  }
  /* The section and cover settings (EXA-164): label above its control, full width. */
  .pbody :global(.settings) {
    display: grid;
    gap: var(--s3);
    min-width: 0;
    margin: 0;
    padding: 0;
    border: 0;
  }
  .pbody :global(.settings:disabled) {
    opacity: 0.6;
  }

  .pbody :global(.settings .row) {
    display: grid;
    gap: var(--s1);
  }
  .pbody :global(.settings .row > span),
  .pbody :global(.settings .check > span) {
    color: var(--ink-soft);
  }
  .pbody :global(.settings :is(input:not([type='checkbox']), select, textarea)) {
    width: 100%;
    box-sizing: border-box;
    min-height: 30px;
    padding: var(--s1) var(--s2);
    border: 1px solid var(--line);
    border-radius: var(--r-sm);
    background: var(--page);
    color: var(--ink);
    font: inherit;
  }
  .pbody :global(.settings textarea) {
    resize: vertical;
  }
  .pbody :global(.settings input.num) {
    width: 88px;
  }
  .pbody :global(.settings .check) {
    display: flex;
    align-items: center;
    gap: var(--s2);
  }
  .pbody :global(.settings .hint) {
    margin: calc(-1 * var(--s2)) 0 0;
    font-size: 12px;
    color: var(--ink-faint);
  }
  .pbody :global(.settings .summary) {
    margin: 0;
    font-weight: 600;
    color: var(--ink-soft);
  }
  .pbody :global(.settings .summary[data-state='over']),
  .pbody :global(.settings .summary[data-state='under']) {
    color: var(--mark);
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
