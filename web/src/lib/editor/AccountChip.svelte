<script lang="ts">
  // Who you are, your data, and sign out. Hidden for the local development stub (nothing to
  // sign out of). Export and delete live behind the name: delete needs the word DELETE typed.
  import { deleteAccount, exportAccountData, session, signOut } from '../session'

  let open = false
  let confirming = false
  let typed = ''
  let busy = false
  let error = ''

  $: user = $session.status === 'user' ? $session.user : null

  function close(): void {
    open = false
    confirming = false
    typed = ''
    error = ''
  }

  async function download(): Promise<void> {
    busy = true
    error = ''
    try {
      const url = URL.createObjectURL(await exportAccountData())
      const a = document.createElement('a')
      a.href = url
      a.download = 'exam-paper-data.zip'
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      error = 'Could not export your data. Try again.'
    } finally {
      busy = false
    }
  }

  async function erase(): Promise<void> {
    busy = true
    error = ''
    try {
      await deleteAccount()
    } catch {
      error = 'Could not delete your account. Nothing was changed.'
      busy = false
    }
  }
</script>

{#if user && !user.dev}
  <span class="chip">
    <button class="who" aria-expanded={open} title={user.email ?? ''} on:click={() => (open ? close() : (open = true))}>
      {user.name ?? user.email ?? 'Signed in'}
    </button>
    <button on:click={signOut}>Sign out</button>
    {#if open}
      <div class="panel" role="dialog" aria-label="Your account">
        {#if !confirming}
          <button disabled={busy} on:click={download}>Download my data</button>
          <p class="hint">A zip of your papers, bank questions and images.</p>
          <button class="danger" on:click={() => (confirming = true)}>Delete my account…</button>
        {:else}
          <p class="warn">
            This permanently deletes your account, all your papers, your question bank and your images. It cannot be
            undone. Download your data first if you want a copy.
          </p>
          <label>
            <span>Type <strong>DELETE</strong> to confirm</span>
            <input bind:value={typed} autocomplete="off" spellcheck="false" />
          </label>
          <div class="row">
            <button class="danger" disabled={typed !== 'DELETE' || busy} on:click={erase}>Delete everything</button>
            <button disabled={busy} on:click={() => ((confirming = false), (typed = ''))}>Cancel</button>
          </div>
        {/if}
        {#if error}<p class="error" role="alert">{error}</p>{/if}
        <button class="link" on:click={close}>Close</button>
      </div>
    {/if}
  </span>
{/if}

<style>
  .chip {
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 13px;
    color: var(--ink-soft);
  }
  .who {
    max-width: 12rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    border-color: transparent;
    background: none;
  }
  button {
    font: inherit;
    font-size: 12.5px;
    border: 1px solid var(--line);
    background: var(--paper);
    color: var(--ink);
    border-radius: 6px;
    padding: 0.2rem 0.6rem;
    cursor: pointer;
  }
  button:disabled {
    opacity: 0.5;
    cursor: default;
  }
  .panel {
    position: absolute;
    top: 100%;
    right: 0;
    z-index: 20;
    width: 19rem;
    margin-top: 0.4rem;
    padding: 0.8rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    background: var(--paper);
    border: 1px solid var(--line);
    border-radius: 8px;
    box-shadow: 0 6px 20px rgb(0 0 0 / 12%);
    color: var(--ink);
  }
  p {
    margin: 0;
  }
  .hint {
    color: var(--ink-faint);
    font-size: 12px;
  }
  .warn {
    color: var(--mark);
  }
  .error {
    color: var(--mark);
  }
  label {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }
  input {
    font: inherit;
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 0.25rem 0.4rem;
  }
  .row {
    display: flex;
    gap: 0.5rem;
  }
  .danger {
    color: var(--mark);
    border-color: var(--mark);
  }
  .link {
    align-self: flex-end;
    border: none;
    background: none;
    color: var(--ink-soft);
  }
</style>
