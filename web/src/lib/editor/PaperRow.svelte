<script lang="ts">
  // One paper on "Your papers" (EXA-166): its title links to the editor, the line under it says
  // the marks and when it was last edited, and a ⋯ menu holds Open, Rename, Move, Make a copy and
  // Delete. With a mouse the ⋯ shows on hover or focus; on touch it is always there.
  // Shift+F10, the Menu key or a right-click on the row (not on the title link, which keeps the
  // browser's own menu) opens the menu too. Rename edits the title in place: Enter saves, Escape
  // backs out, and focus goes back to the ⋯ button.
  import { tick } from 'svelte'
  import Icon from '../Icon.svelte'
  import Menu, { type MenuItem } from '../Menu.svelte'
  import { editedWhen, fullDate } from '../dates'
  import { navigate } from '../router'
  import type { DocumentSummary } from './doc'

  let {
    doc,
    now,
    canMove,
    onRename,
    onMove,
    onCopy,
    onDelete,
  }: {
    doc: DocumentSummary
    /** The list's clock, so every row's relative time agrees and ticks on together. */
    now: Date
    /** There is a folder to move to; without one, Move says to make a folder first. */
    canMove: boolean
    onRename: (title: string) => Promise<boolean>
    onMove: () => void
    onCopy: () => void
    onDelete: () => void
  } = $props()

  let menu: { openMenu: () => void; focusTrigger: () => void } | undefined = $state()
  let renaming = $state(false)
  let busy = $state(false)
  let name = $state('')
  let input: HTMLInputElement | undefined = $state()

  const title = $derived(doc.title || 'Untitled paper')

  async function startRename() {
    name = doc.title
    renaming = true
    await tick()
    input?.focus()
    input?.select()
  }

  async function endRename() {
    renaming = false
    await tick()
    menu?.focusTrigger()
  }

  async function saveRename(e: SubmitEvent) {
    e.preventDefault()
    const trimmed = name.trim()
    if (!trimmed || busy) return
    if (trimmed === doc.title) return endRename()
    busy = true
    const ok = await onRename(trimmed)
    busy = false
    if (ok) await endRename()
  }

  function onRowKey(e: KeyboardEvent) {
    if ((e.key === 'F10' && e.shiftKey) || e.key === 'ContextMenu') {
      e.preventDefault()
      menu?.openMenu()
    }
  }

  function onContext(e: MouseEvent) {
    // over the title the browser's own menu stays (Open in new tab, Copy link)
    if ((e.target as Element | null)?.closest?.('a')) return
    e.preventDefault()
    menu?.openMenu()
  }

  const items: MenuItem[] = $derived([
    { label: 'Open', icon: 'open', onSelect: () => navigate(`/docs/${doc.id}`) },
    { label: 'Rename', icon: 'pen', onSelect: () => void startRename() },
    {
      label: 'Move to folder…',
      icon: 'folder',
      disabled: !canMove,
      hint: canMove ? undefined : 'Make a folder first, with + New.',
      onSelect: onMove,
    },
    { label: 'Make a copy', icon: 'copy', onSelect: onCopy },
    { label: 'Delete…', icon: 'trash', danger: true, separator: true, onSelect: onDelete },
  ])
</script>

<li class="row" data-doc-id={doc.id} oncontextmenu={renaming ? undefined : onContext}>
  {#if renaming}
    <form class="rename" aria-label={`Rename “${title}”`} onsubmit={saveRename}>
      <input
        bind:this={input}
        bind:value={name}
        aria-label="Paper title"
        maxlength="200"
        required
        onkeydown={(e) => {
          if (e.key === 'Escape') {
            e.preventDefault()
            void endRename()
          }
        }}
      />
      <button class="btn primary" type="submit" disabled={busy || !name.trim()}>Save</button>
      <button class="btn" type="button" disabled={busy} onclick={endRename}>Cancel</button>
    </form>
  {:else}
    <a class="open" href={`#/docs/${doc.id}`} onkeydown={onRowKey}>
      <span class="t">{title}</span>
      <span class="m"
        >{doc.total_marks} marks · edited <time datetime={doc.updated_at} title={fullDate(doc.updated_at)}
          >{editedWhen(doc.updated_at, now)}</time
        ></span
      >
    </a>
  {/if}
  <Menu
    bind:this={menu}
    {items}
    label={`Actions for “${title}”`}
    menuLabel={title}
    align="end"
    triggerClass="more"
    triggerTitle="Actions (Shift+F10)"
  >
    {#snippet trigger()}<Icon name="more" />{/snippet}
  </Menu>
</li>

<style>
  .row {
    display: flex;
    align-items: center;
    gap: var(--s3);
    min-height: 56px;
    padding: var(--s2) var(--s2) var(--s2) var(--s4);
    border-top: 1px solid var(--line-soft);
  }
  .row:first-child {
    border-top: 0;
  }
  /* the list box has rounded corners and does not clip (the menu must overflow it) */
  .row:last-child {
    border-radius: 0 0 calc(var(--r-md) - 1px) calc(var(--r-md) - 1px);
  }
  .row:first-child:last-child {
    border-radius: calc(var(--r-md) - 1px);
  }
  .row:hover {
    background: var(--wash);
  }
  .open {
    flex: 1;
    min-width: 0;
    display: grid;
    gap: 2px;
    padding: 2px 0;
    color: inherit;
    text-decoration: none;
    border-radius: 4px;
  }
  .open:focus-visible {
    outline: 2px solid var(--verify);
    outline-offset: 2px;
  }
  .t {
    font-weight: 600;
    font-size: 14.5px;
    overflow-wrap: anywhere;
  }
  .open:hover .t {
    text-decoration: underline;
    text-decoration-color: var(--line);
    text-underline-offset: 3px;
  }
  .m {
    font-size: 12.5px;
    color: var(--ink-faint);
  }
  .row :global(.more) {
    display: inline-grid;
    place-items: center;
    width: 32px;
    height: 32px;
    padding: 0;
    border: 1px solid transparent;
    border-radius: var(--r-sm);
    background: none;
    color: var(--ink-soft);
    cursor: pointer;
  }
  .row :global(.more:hover),
  .row :global(.more[aria-expanded='true']) {
    background: var(--page);
    border-color: var(--line);
    color: var(--ink);
  }
  .row :global(.more:focus-visible) {
    outline: 2px solid var(--verify);
    outline-offset: 1px;
  }
  /* A mouse shows the ⋯ on hover or focus; touch screens (and hybrid ones) always show it. */
  @media (hover: hover) and (pointer: fine) {
    .row :global(.more) {
      opacity: 0;
    }
    .row:hover :global(.more),
    .row:focus-within :global(.more),
    .row :global(.more[aria-expanded='true']) {
      opacity: 1;
    }
  }
  .rename {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-wrap: wrap;
    gap: var(--s2);
    align-items: center;
  }
  .rename input {
    flex: 1 1 12rem;
    min-width: 0;
    height: 32px;
    box-sizing: border-box;
    font: inherit;
    font-size: 14px;
    border: 1px solid var(--line);
    border-radius: var(--r-sm);
    background: var(--page);
    color: var(--ink);
    padding: 0 var(--s2);
  }
  .rename input:focus-visible,
  .btn:focus-visible {
    outline: 2px solid var(--verify);
    outline-offset: 2px;
  }
  .btn {
    font: inherit;
    font-size: 13px;
    font-weight: 600;
    height: 32px;
    padding: 0 var(--s3);
    border: 1px solid var(--line);
    border-radius: var(--r-sm);
    background: var(--page);
    color: var(--ink);
    cursor: pointer;
  }
  .btn.primary {
    background: var(--verify);
    border-color: var(--verify);
    color: var(--on-accent);
  }
  .btn:disabled {
    opacity: 0.5;
    cursor: default;
  }
</style>
