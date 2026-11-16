<script lang="ts">
  // O2: one folder on "Your papers" — its name, the exam-set chips, rename and delete (inline,
  // delete asks first and says the papers stay), and its papers (the default slot).
  import { tick } from 'svelte'
  import { PARTS, type FolderGroup } from './folders'

  export let group: FolderGroup
  export let onRename: (name: string) => Promise<boolean>
  export let onDelete: () => Promise<void>
  /** O3: open the + New wizard with this folder as the home for what it makes. */
  export let onNew: (e: Event) => void

  let renaming = false
  let name = ''
  let confirming = false
  let busy = false
  let nameInput: HTMLInputElement
  let renameButton: HTMLButtonElement
  let deleteButton: HTMLButtonElement
  let cancelDelete: HTMLButtonElement

  $: f = group.folder
  $: count = group.docs.length
  $: headingId = `folder-${f.id}`

  async function startRename() {
    confirming = false
    name = f.name
    renaming = true
    await tick()
    nameInput?.select()
  }

  async function endRename() {
    renaming = false
    await tick()
    renameButton?.focus()
  }

  async function saveRename() {
    const trimmed = name.trim()
    if (!trimmed || busy) return
    if (trimmed === f.name) return endRename()
    busy = true
    const ok = await onRename(trimmed)
    busy = false
    if (ok) await endRename()
  }

  async function askDelete() {
    renaming = false
    confirming = true
    await tick()
    cancelDelete?.focus()
  }

  async function endDelete() {
    confirming = false
    await tick()
    deleteButton?.focus()
  }

  async function confirmDelete() {
    busy = true
    await onDelete()
    busy = false
  }

  const papers = (n: number): string => `${n} ${n === 1 ? 'paper' : 'papers'}`
</script>

<section class="folder" aria-labelledby={headingId}>
  <div class="fhead">
    <svg class="ficon" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path d="M3 6.5A1.5 1.5 0 0 1 4.5 5h4.6l2 2h8.4A1.5 1.5 0 0 1 21 8.5v9a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 17.5z" />
    </svg>
    {#if renaming}
      <form class="rename" aria-label={`Rename folder “${f.name}”`} on:submit|preventDefault={saveRename}>
        <input
          bind:this={nameInput}
          bind:value={name}
          aria-label="Folder name"
          maxlength="80"
          required
          on:keydown={(e) => e.key === 'Escape' && endRename()}
        />
        <button class="act primary" type="submit" disabled={busy || !name.trim()}>Save</button>
        <button class="act" type="button" on:click={endRename}>Cancel</button>
      </form>
      <h2 id={headingId} class="sr">{f.name}</h2>
    {:else}
      <h2 id={headingId} tabindex="-1">{f.name}</h2>
      <span class="count">{papers(count)}</span>
      <div class="actions">
        <button class="act" aria-haspopup="dialog" aria-label={`+ New in folder “${f.name}”`} on:click={onNew}>
          + New in folder
        </button>
        <button class="act" bind:this={renameButton} aria-label={`Rename folder “${f.name}”`} on:click={startRename}>
          Rename
        </button>
        <button class="act danger" bind:this={deleteButton} aria-label={`Delete folder “${f.name}”`} on:click={askDelete}>
          Delete
        </button>
      </div>
    {/if}
  </div>

  <ul class="chips" aria-label={`Exam set in “${f.name}”`}>
    {#each PARTS as p (p.key)}
      {@const on = group.parts.has(p.key)}
      <li class="chip" class:on data-part={p.key}>
        {#if on}
          <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M9.5 16.2 5.3 12l-1.4 1.4 5.6 5.6 11-11-1.4-1.4z" /></svg>
        {/if}
        {p.label}<span class="sr">{on ? ': in this folder' : ': not in this folder yet'}</span>
      </li>
    {/each}
  </ul>

  {#if confirming}
    <div class="confirm" role="group" aria-label={`Delete folder “${f.name}”?`}>
      <p>
        Delete the folder <b>{f.name}</b>?
        {#if count > 0}Its {papers(count)} will move to Unfiled.{/if} No paper is deleted.
      </p>
      <button class="act danger-fill" disabled={busy} on:click={confirmDelete}>Delete folder</button>
      <button class="act" bind:this={cancelDelete} on:click={endDelete}>Cancel</button>
    </div>
  {/if}

  {#if count === 0}
    <p class="empty">No papers in this folder yet. Use <b>+ New in folder</b>, or <b>Move</b> on a paper to file it here.</p>
  {:else}
    <slot />
  {/if}
</section>

<style>
  .folder {
    border: 1px solid var(--line);
    border-radius: 12px;
    background: var(--wash);
    padding: 0.8rem 0.9rem 0.9rem;
  }
  .fhead {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    min-height: 32px;
  }
  .ficon {
    flex: none;
    fill: var(--ink-faint);
  }
  h2 {
    font-family: var(--serif);
    font-size: 1.05rem;
    font-weight: 600;
    margin: 0;
    overflow-wrap: anywhere;
  }
  .count {
    font-size: 12px;
    color: var(--ink-faint);
    white-space: nowrap;
  }
  .actions {
    margin-left: auto;
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 0.4rem;
  }
  h2:focus {
    outline: none;
  }
  h2 {
    scroll-margin-top: 1.5rem;
  }
  h2:focus-visible {
    outline: 2px solid var(--verify);
    outline-offset: 2px;
  }
  .rename {
    flex: 1;
    display: flex;
    gap: 0.4rem;
    align-items: center;
  }
  .rename input {
    flex: 1;
    min-width: 0;
    font: inherit;
    font-size: 14px;
    border: 1px solid var(--line);
    border-radius: 6px;
    background: var(--page);
    color: var(--ink);
    padding: 0.3rem 0.5rem;
  }
  .act {
    font: inherit;
    font-size: 12px;
    border: 1px solid var(--line);
    background: var(--page);
    border-radius: 6px;
    padding: 0.25rem 0.6rem;
    color: var(--ink-soft);
    cursor: pointer;
  }
  .act.primary {
    border-color: var(--verify);
    background: var(--verify);
    color: #fff;
  }
  .act.danger {
    color: var(--mark);
  }
  .act.danger-fill {
    border-color: var(--mark);
    background: var(--mark);
    color: #fff;
  }
  .act:disabled {
    opacity: 0.6;
    cursor: default;
  }
  .act:focus-visible,
  .rename input:focus-visible {
    outline: 2px solid var(--verify);
    outline-offset: 2px;
  }

  /* M3 filter chips on our tokens: 32px tall, 8px corners, an outline when off; filled with the
     secondary-container analogue (verify-soft) and a leading check when the folder has that part.
     They report state, so there is no press layer. */
  .chips {
    list-style: none;
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    padding: 0;
    margin: 0.55rem 0 0.7rem;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    height: 32px;
    box-sizing: border-box;
    padding: 0 0.85rem;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--page);
    color: var(--ink-faint);
    font-size: 13px;
    font-weight: 600;
  }
  .chip.on {
    border-color: transparent;
    background: var(--verify-soft);
    color: var(--verify-ink);
    padding-left: 0.5rem;
  }
  .chip svg {
    fill: currentColor;
  }

  .confirm {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.4rem 0.5rem;
    border: 1px solid var(--mark);
    background: var(--mark-soft);
    border-radius: 8px;
    padding: 0.55rem 0.7rem;
    margin-bottom: 0.7rem;
  }
  .confirm p {
    flex: 1 1 18rem;
    margin: 0;
    font-size: 13px;
    color: var(--ink);
  }
  .empty {
    margin: 0;
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
