<script lang="ts">
  // The editor header's first row (EXA-160): back, folder / title, save state, the marks total,
  // Preview, the one primary action (Export ▾) and the account avatar. Paper settings live in the
  // side panel, never here. The Paper / Insert / View / Help menus (EXA-163) sit under the
  // title, passed in as `menus`. The Paper / Answer key switch (EXA-162) sits before the total;
  // below 1200 px it is an icon pair. Narrow windows drop the folder and the resting marks total (the panel shows it);
  // Preview and Export always stay on screen. On a generated paper with placeholders still to
  // write, a quiet link beside the total says how many and opens the side panel's Paper tab.
  import type { Snippet } from 'svelte'
  import Icon from '../Icon.svelte'
  import { ariaKeys, keyLabel } from '../keys'
  import { GLOBAL_KEYS } from './shortcuts'
  import Menu, { type MenuItem } from '../Menu.svelte'
  import AccountMenu from './AccountMenu.svelte'
  import type { ExportMode } from './docsApi'
  import type { Quota } from '../session'

  type Status = 'saved' | 'dirty' | 'saving' | 'conflict' | 'error'

  let {
    title,
    folderName = null,
    status,
    marks,
    target = null,
    offTarget = '',
    busy = '',
    hasQuestions,
    quota = null,
    placeholdersLeft = 0,
    onShowPlaceholders = () => {},
    onPreview,
    onExport,
    onRename,
    view = 'paper',
    onView = () => {},
    menus,
  }: {
    title: string
    folderName?: string | null
    status: Status
    marks: number
    /** The sum of the sections' marks targets, when every section has one. */
    target?: number | null
    /** Why the marks are off (e.g. "Section B: 47 of 45 marks"); empty when on target. */
    offTarget?: string
    busy?: string
    hasQuestions: boolean
    quota?: Quota | null
    /** Generated placeholders the teacher has not written yet. */
    placeholdersLeft?: number
    onShowPlaceholders?: () => void
    onPreview: () => void
    onExport: (mode: ExportMode) => void
    onRename: () => void
    /** What the page shows: the paper, or its answer key as it prints. */
    view?: 'paper' | 'key'
    onView?: (view: 'paper' | 'key') => void
    /** The menu row under the title. */
    menus?: Snippet
  } = $props()

  const STATUS: Record<Status, string> = {
    saved: 'Saved',
    dirty: 'Unsaved changes',
    saving: 'Saving…',
    conflict: 'Conflict',
    error: 'Save failed — will retry',
  }

  const exporting = $derived(busy.startsWith('export-'))
  const items = $derived<MenuItem[]>([
    { label: 'Student paper (PDF)', onSelect: () => onExport('student') },
    {
      label: 'Answer key (PDF)',
      onSelect: () => onExport('key'),
      disabled: !hasQuestions,
      hint: hasQuestions ? undefined : 'Add a question first: the key has nothing to show yet.',
    },
    { label: 'Paper and key together (PDF)', onSelect: () => onExport('full') },
  ])
</script>

<div class="row1">
  <a class="icon-btn" href="#/" aria-label="Back to papers" title="Back to papers"><Icon name="back" /></a>
  <div class="titleblock">
    <div class="crumb">
      {#if folderName}<span class="cfolder">{folderName} /</span>{/if}
      <button class="title" title="Rename: edit the title on the page" onclick={onRename}
        >{title || 'Untitled paper'}</button
      >
      <span class="saved {status}" role="status" aria-live="polite">
        {#if status === 'saved'}<Icon name="check" size={14} />{/if}{STATUS[status]}
      </span>
    </div>
    {#if menus}{@render menus()}{/if}
  </div>
  <div class="seg" role="group" aria-label="View">
    <button
      aria-pressed={view === 'paper'}
      title="Paper"
      onclick={() => onView('paper')}><Icon name="blankpage" /><span class="seg-txt">Paper</span></button
    >
    <button
      aria-pressed={view === 'key'}
      title="Answer key ({keyLabel(GLOBAL_KEYS.answerKey)})"
      aria-keyshortcuts={ariaKeys(GLOBAL_KEYS.answerKey)}
      onclick={() => onView('key')}><Icon name="key" /><span class="seg-txt">Answer key</span></button
    >
  </div>
  <span class="total" class:off={!!offTarget} title={offTarget || undefined} data-testid="marks-total">
    {#if offTarget}<Icon name="alert" size={14} />{/if}<b>{marks}</b>{target === null ? '' : ` / ${target}`} marks
    {#if offTarget}<span class="sr">({offTarget})</span>{/if}
  </span>
  {#if placeholdersLeft}
    <button
      class="towrite"
      title="Generated placeholders still to write: see the Paper tab"
      data-testid="header-placeholders"
      onclick={onShowPlaceholders}
      >{placeholdersLeft}<span class="wide">{placeholdersLeft === 1 ? ' placeholder' : ' placeholders'}</span> to write</button
    >
  {/if}
  <button
    class="btn"
    disabled={!!busy}
    title="Preview pages ({keyLabel(GLOBAL_KEYS.preview)})"
    aria-keyshortcuts={ariaKeys(GLOBAL_KEYS.preview)}
    onclick={onPreview}
  >
    <Icon name="eye" /><span class="btn-txt">Preview</span>
  </button>
  <Menu {items} align="end" triggerClass="btn primary" disabled={!!busy} label={exporting ? 'Exporting…' : 'Export'}>
    {#snippet trigger()}<Icon name="export" /><span class="btn-txt">{exporting ? 'Exporting…' : 'Export'}</span><Icon
        name="down"
      />{/snippet}
    {#snippet footer()}
      {#if quota && typeof quota.left_day === 'number'}
        <span title="PDF exports left in the last 24 hours">{quota.left_day} exports left today</span>
      {:else}
        <span>PDFs are A4, ready to print</span>
      {/if}
    {/snippet}
  </Menu>
  <AccountMenu />
</div>

<style>
  .row1 {
    display: flex;
    align-items: center;
    gap: var(--s3);
    min-height: 52px;
    padding: var(--s2) var(--s4) 0;
  }
  .titleblock {
    flex: 1;
    min-width: 0;
  }
  .crumb {
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
    font-size: 15px;
  }
  .cfolder {
    color: var(--ink-faint);
    white-space: nowrap;
  }
  .title {
    min-width: 0;
    padding: 0 2px;
    border: 0;
    border-radius: 4px;
    background: none;
    color: var(--ink);
    font: inherit;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    cursor: text;
  }
  .title:hover {
    background: var(--wash);
  }
  .saved {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    margin-left: var(--s2);
    font-size: 12px;
    color: var(--ink-faint);
    white-space: nowrap;
  }
  .saved.conflict,
  .saved.error {
    color: var(--mark);
    font-weight: 600;
  }
  /* Paper | Answer key: a two-way segmented control, the Settings page's pill */
  .seg {
    display: inline-flex;
    flex: none;
    padding: 2px;
    border: 1px solid var(--line);
    border-radius: var(--r-md);
    background: var(--wash);
  }
  .seg button {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 28px;
    padding: 0 10px;
    border: 0;
    border-radius: var(--r-sm);
    background: none;
    color: var(--ink-soft);
    font: inherit;
    font-size: 13px;
    white-space: nowrap;
    cursor: pointer;
  }
  .seg button :global(svg) {
    display: none;
  }
  .seg button:hover {
    color: var(--ink);
  }
  .seg button[aria-pressed='true'] {
    background: var(--page);
    color: var(--ink);
    font-weight: 600;
    box-shadow: 0 0 0 1px var(--line);
  }
  .total {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 13px;
    color: var(--ink-soft);
    white-space: nowrap;
  }
  .total b {
    color: var(--ink);
    font-weight: 600;
  }
  .total.off,
  .total.off b {
    color: var(--mark);
  }
  .towrite {
    flex: none;
    padding: 2px 4px;
    border: 0;
    border-radius: 4px;
    background: none;
    color: var(--mark);
    font: inherit;
    font-size: 13px;
    white-space: nowrap;
    text-decoration: underline dotted;
    text-underline-offset: 3px;
    cursor: pointer;
  }
  .towrite:hover {
    background: var(--wash);
  }
  .icon-btn {
    display: inline-grid;
    place-items: center;
    flex: none;
    width: 32px;
    height: 32px;
    border-radius: var(--r-sm);
    color: var(--ink-soft);
  }
  .icon-btn:hover {
    background: var(--wash);
    color: var(--ink);
  }
  .row1 :global(.btn) {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    flex: none;
    height: 32px;
    padding: 0 var(--s3);
    border: 1px solid var(--line);
    border-radius: var(--r-sm);
    background: var(--page);
    color: var(--ink);
    font: inherit;
    font-size: 13px;
    font-weight: 600;
    white-space: nowrap;
    cursor: pointer;
  }
  .row1 :global(.btn:hover:not(:disabled)) {
    background: var(--wash);
  }
  .row1 :global(.btn.primary) {
    background: var(--verify);
    border-color: var(--verify);
    color: var(--on-accent);
  }
  .row1 :global(.btn.primary:hover:not(:disabled)) {
    background: var(--verify-ink);
  }
  .row1 :global(.btn:disabled) {
    opacity: 0.6;
    cursor: default;
  }
  .sr {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
  }
  @media (max-width: 1199px) {
    .total:not(.off) {
      display: none;
    }
    .seg button {
      width: 32px;
      padding: 0;
      justify-content: center;
    }
    .seg button :global(svg) {
      display: block;
    }
    .seg-txt {
      position: absolute;
      width: 1px;
      height: 1px;
      overflow: hidden;
      clip: rect(0 0 0 0);
      white-space: nowrap;
    }
    .wide {
      position: absolute;
      width: 1px;
      height: 1px;
      overflow: hidden;
      clip: rect(0 0 0 0);
      white-space: nowrap;
    }
  }
  @media (max-width: 899px) {
    .cfolder {
      display: none;
    }
  }
  @media (max-width: 599px) {
    /* a phone keeps the title: the switch is in Menu > View there */
    .seg {
      display: none;
    }
    .btn-txt {
      position: absolute;
      width: 1px;
      height: 1px;
      overflow: hidden;
      clip: rect(0 0 0 0);
    }
  }
</style>
