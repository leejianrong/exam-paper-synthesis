<script lang="ts">
  // Paper > Move to folder… (EXA-163): pick a folder (or Unfiled) and move the paper there.
  // Moving is not an edit: the paper's version stays, so the open editor saves on as before.
  import Dialog from '../Dialog.svelte'
  import type { Folder } from './docsApi'

  let {
    folders,
    current,
    busy = false,
    error = '',
    onMove,
    onClose,
  }: {
    folders: Folder[]
    current: string | null
    busy?: boolean
    error?: string
    onMove: (folderId: string | null) => void
    onClose: () => void
  } = $props()

  // the current place is where the choice starts
  // svelte-ignore state_referenced_locally
  let choice = $state<string>(current ?? '')

  // While the move runs the dialog stays, so a failure still has somewhere to show.
  const close = () => {
    if (!busy) onClose()
  }
</script>

<Dialog title="Move to folder" width="24rem" onClose={close}>
  <form
    onsubmit={(e) => {
      e.preventDefault()
      onMove(choice || null)
    }}
  >
    <fieldset>
      <legend class="sr">Folder</legend>
      {#each folders as f (f.id)}
        <label><input type="radio" name="folder" value={f.id} bind:group={choice} /> {f.name}</label>
      {/each}
      <label><input type="radio" name="folder" value="" bind:group={choice} /> Unfiled</label>
    </fieldset>
    {#if !folders.length}<p class="hint">You have no folders yet: make one on the papers list.</p>{/if}
    {#if error}<p class="error" role="alert">{error}</p>{/if}
    <div class="row">
      <button class="primary" type="submit" disabled={busy || choice === (current ?? '')}>Move</button>
      <button type="button" disabled={busy} onclick={close}>Cancel</button>
    </div>
  </form>
</Dialog>

<style>
  fieldset {
    display: flex;
    flex-direction: column;
    gap: 2px;
    margin: 0 0 var(--s4);
    padding: 0;
    border: 0;
    max-height: 18rem;
    overflow-y: auto;
  }
  label {
    display: flex;
    align-items: center;
    gap: var(--s2);
    padding: 6px var(--s2);
    border-radius: 4px;
    cursor: pointer;
  }
  label:hover {
    background: var(--wash);
  }
  .row {
    display: flex;
    gap: var(--s2);
  }
  button {
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
  button:hover:not(:disabled) {
    background: var(--wash);
  }
  .primary {
    background: var(--verify);
    border-color: var(--verify);
    color: var(--on-accent);
  }
  .primary:hover:not(:disabled) {
    background: var(--verify-ink);
  }
  button:disabled {
    opacity: 0.5;
    cursor: default;
  }
  .hint {
    margin: 0 0 var(--s3);
    color: var(--ink-soft);
  }
  .error {
    color: var(--mark);
    font-size: 12.5px;
  }
  .sr {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
  }
</style>
