<script lang="ts">
  // The editor header's first row (EXA-160): back, folder / title, save state, the marks total,
  // Preview, the one primary action (Export ▾) and the account avatar. Paper settings live in the
  // side panel, never here. Room is left after the title for the Paper / Insert / View / Help
  // menus (S5). Narrow windows drop the folder and the resting marks total (the panel shows it);
  // Preview and Export always stay on screen.
  import Icon from '../Icon.svelte'
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
    onPreview,
    onExport,
    onRename,
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
    onPreview: () => void
    onExport: (mode: ExportMode) => void
    onRename: () => void
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
  </div>
  <span class="total" class:off={!!offTarget} title={offTarget || undefined} data-testid="marks-total">
    {#if offTarget}<Icon name="alert" size={14} />{/if}<b>{marks}</b>{target === null ? '' : ` / ${target}`} marks
    {#if offTarget}<span class="sr">({offTarget})</span>{/if}
  </span>
  <button class="btn" disabled={!!busy} onclick={onPreview}>
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
    /* S5's menus (Paper, Insert, View, Help) go under the crumb */
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
  }
  @media (max-width: 899px) {
    .cfolder {
      display: none;
    }
  }
  @media (max-width: 599px) {
    .btn-txt {
      position: absolute;
      width: 1px;
      height: 1px;
      overflow: hidden;
      clip: rect(0 0 0 0);
    }
  }
</style>
