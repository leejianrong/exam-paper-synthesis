<script lang="ts">
  // O2, reworked for EXA-166: one folder on "Your papers". Its name is a disclosure button that
  // collapses the folder (the list remembers which); a ⋯ menu holds New paper in folder, Rename
  // (inline: Enter saves, Escape backs out) and Delete (the list confirms it). While the list is
  // searched the name is plain text and the folder stays open.
  import { tick, type Snippet } from 'svelte'
  import Icon from '../Icon.svelte'
  import Menu, { type MenuItem } from '../Menu.svelte'
  import type { FolderGroup } from './folders'

  let {
    group,
    collapsed,
    collapsible = true,
    onToggle,
    onRename,
    onDelete,
    onNew,
    children,
  }: {
    group: FolderGroup
    collapsed: boolean
    /** False while searching: the folder shows its matches and cannot be collapsed. */
    collapsible?: boolean
    onToggle: () => void
    onRename: (name: string) => Promise<boolean>
    onDelete: () => void
    /** O3: open the + New wizard with this folder as the home for what it makes. */
    onNew: () => void
    children: Snippet
  } = $props()

  let renaming = $state(false)
  let name = $state('')
  let busy = $state(false)
  let nameInput: HTMLInputElement | undefined = $state()
  let menu: { focusTrigger: () => void } | undefined = $state()

  const f = $derived(group.folder)
  const count = $derived(group.docs.length)
  const headingId = $derived(`folder-${f.id}`)
  const bodyId = $derived(`folder-body-${f.id}`)
  const papers = (n: number): string => `${n} ${n === 1 ? 'paper' : 'papers'}`

  async function startRename() {
    name = f.name
    renaming = true
    await tick()
    nameInput?.focus()
    nameInput?.select()
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
    if (trimmed === f.name) return endRename()
    busy = true
    const ok = await onRename(trimmed)
    busy = false
    if (ok) await endRename()
  }

  const items: MenuItem[] = $derived([
    { label: 'New paper in folder…', icon: 'plus', onSelect: onNew },
    { label: 'Rename folder', icon: 'pen', onSelect: () => void startRename() },
    { label: 'Delete folder…', icon: 'trash', danger: true, separator: true, onSelect: onDelete },
  ])
  const open = $derived(!collapsible || !collapsed)
</script>

<section class="folder" aria-labelledby={headingId}>
  <div class="fhead">
    {#if renaming}
      <Icon name="folder" />
      <form class="rename" aria-label={`Rename folder “${f.name}”`} onsubmit={saveRename}>
        <input
          bind:this={nameInput}
          bind:value={name}
          aria-label="Folder name"
          maxlength="80"
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
      <h2 id={headingId} class="sr">{f.name}</h2>
    {:else}
      <h2 id={headingId} tabindex="-1">
        {#if collapsible}
          <button
            type="button"
            class="toggle"
            aria-expanded={!collapsed}
            aria-controls={bodyId}
            title={collapsed ? 'Show the papers' : 'Hide the papers'}
            onclick={onToggle}
          >
            <span class="chev" class:shut={collapsed}><Icon name="down" /></span><Icon name="folder" /><span
              class="name">{f.name}</span
            >
          </button>
        {:else}
          <span class="toggle static"><Icon name="folder" /><span class="name">{f.name}</span></span>
        {/if}
      </h2>
      <!-- while searching (not collapsible) the folder lists only its matches -->
      <span class="count">{collapsible ? papers(count) : `${count} ${count === 1 ? 'match' : 'matches'}`}</span>
    {/if}
    <span class="end">
      <Menu bind:this={menu} {items} label={`Actions for folder “${f.name}”`} menuLabel={f.name} align="end" triggerClass="more">
        {#snippet trigger()}<Icon name="more" />{/snippet}
      </Menu>
    </span>
  </div>

  <!-- kept mounted when collapsed, so the toggle's aria-controls always names it -->
  <div id={bodyId} class="body" hidden={!open}>
    {#if open}
      {#if count === 0}
        <p class="empty">No papers here yet. Make one from this folder’s ⋯ menu, or move a paper in.</p>
      {:else}
        {@render children()}
      {/if}
    {/if}
  </div>
</section>

<style>
  .folder {
    background: var(--page);
    border: 1px solid var(--line);
    border-radius: var(--r-md);
  }
  .fhead {
    display: flex;
    align-items: center;
    gap: var(--s2);
    min-height: 48px;
    padding: var(--s2) var(--s2) var(--s2) var(--s2);
    color: var(--ink-faint);
  }
  h2 {
    margin: 0;
    min-width: 0;
    font-size: 15px;
    font-weight: 600;
    color: var(--ink);
    scroll-margin-top: var(--s6);
  }
  h2:focus {
    outline: none;
  }
  .toggle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    min-height: 32px;
    padding: 0 var(--s2);
    border: 0;
    border-radius: var(--r-sm);
    background: none;
    font: inherit;
    color: inherit;
    text-align: left;
    cursor: pointer;
  }
  .toggle.static {
    cursor: default;
    padding-left: 30px;
  }
  .toggle :global(.icon) {
    flex: none;
    color: var(--ink-faint);
  }
  button.toggle:hover {
    background: var(--wash);
  }
  .toggle:focus-visible {
    outline: 2px solid var(--verify);
    outline-offset: 1px;
  }
  .name {
    overflow-wrap: anywhere;
  }
  .chev {
    display: inline-flex;
    transition: transform 0.12s ease;
  }
  .chev.shut {
    transform: rotate(-90deg);
  }
  @media (prefers-reduced-motion: reduce) {
    .chev {
      transition: none;
    }
  }
  .count {
    font-size: 12.5px;
    white-space: nowrap;
  }
  .end {
    margin-left: auto;
    display: inline-flex;
  }
  .fhead :global(.more) {
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
  .fhead :global(.more:hover),
  .fhead :global(.more[aria-expanded='true']) {
    background: var(--wash);
    color: var(--ink);
  }
  .fhead :global(.more:focus-visible) {
    outline: 2px solid var(--verify);
    outline-offset: 1px;
  }
  .body {
    border-top: 1px solid var(--line-soft);
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
    flex: 1 1 10rem;
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
  .empty {
    margin: 0;
    padding: var(--s3) var(--s4);
    font-size: 13px;
    color: var(--ink-soft);
  }
  .sr {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
  }
</style>
