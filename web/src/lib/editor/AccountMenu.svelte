<script lang="ts">
  // The account avatar (EXA-160; was AccountChip): who you are, Settings, your data, sign out.
  // The local development stub has nothing to sign out of or export, so it gets Settings only.
  // Deleting the account confirms in a dialog that needs the word DELETE typed.
  import { tick } from 'svelte'
  import Menu, { type MenuItem } from '../Menu.svelte'
  import { deleteAccount, exportAccountData, session, signOut } from '../session'

  let confirming = $state(false)
  let typed = $state('')
  let busy = $state(false)
  let error = $state('')
  let field: HTMLInputElement | undefined = $state()

  const user = $derived($session.status === 'user' ? $session.user : null)
  const name = $derived(user?.name ?? user?.email ?? 'Signed in')
  const initials = $derived(
    name
      .split(/[\s@.]+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((w) => w[0]!.toUpperCase())
      .join('') || '?',
  )

  const items = $derived<MenuItem[]>([
    { label: 'Settings', icon: 'settings', onSelect: () => (location.hash = '#/settings') },
    ...(user && !user.dev
      ? [
          { label: 'Download my data', icon: 'download', hint: 'A zip of your papers, bank questions and images.', onSelect: download },
          { label: 'Sign out', icon: 'signout', onSelect: () => void signOut() },
          { label: 'Delete my account…', icon: 'trash', danger: true, separator: true, onSelect: startDelete },
        ] satisfies MenuItem[]
      : []),
  ])

  async function startDelete(): Promise<void> {
    confirming = true
    typed = ''
    error = ''
    await tick()
    field?.focus()
  }

  function cancel(): void {
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

{#if user}
  <Menu {items} label="Account: {name}" align="end" triggerClass="avatar" triggerTitle={user.email ?? name}>
    {#snippet trigger()}{initials}{/snippet}
    {#snippet header()}
      <strong class="who">{name}</strong>
      {#if user.email && user.email !== name}<span class="email">{user.email}</span>{/if}
    {/snippet}
  </Menu>
  {#if error && !confirming}<span class="error" role="alert">{error}</span>{/if}
{/if}

{#if confirming}
  <div class="backdrop" role="presentation" onclick={(e) => e.target === e.currentTarget && !busy && cancel()}>
    <div class="dialog" role="alertdialog" aria-modal="true" aria-labelledby="del-title" aria-describedby="del-body">
      <h2 id="del-title">Delete your account?</h2>
      <p id="del-body" class="warn">
        This permanently deletes your account, all your papers, your question bank and your images. It cannot be undone.
        Download your data first if you want a copy.
      </p>
      <label>
        <span>Type <strong>DELETE</strong> to confirm</span>
        <input bind:this={field} bind:value={typed} autocomplete="off" spellcheck="false" />
      </label>
      {#if error}<p class="error" role="alert">{error}</p>{/if}
      <div class="row">
        <button class="danger" disabled={typed !== 'DELETE' || busy} onclick={erase}>Delete everything</button>
        <button disabled={busy} onclick={cancel}>Cancel</button>
      </div>
    </div>
  </div>
{/if}

<style>
  :global(.avatar) {
    width: 30px;
    height: 30px;
    border-radius: 50%;
    border: 0;
    padding: 0;
    background: var(--ink);
    color: var(--on-accent);
    display: grid;
    place-items: center;
    font: inherit;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
  }
  :global(.avatar:focus-visible) {
    border-radius: 50%;
  }
  .who {
    display: block;
    color: var(--ink);
    font-weight: 600;
  }
  .email {
    display: block;
    font-size: 12px;
    color: var(--ink-faint);
  }
  .error {
    color: var(--mark);
    font-size: 12.5px;
  }
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 60;
    display: grid;
    place-items: center;
    background: rgba(25, 28, 33, 0.5);
  }
  .dialog {
    width: min(26rem, calc(100vw - 2rem));
    padding: var(--s4) var(--s4) var(--s4);
    display: flex;
    flex-direction: column;
    gap: var(--s3);
    background: var(--page);
    color: var(--ink);
    border: 1px solid var(--line);
    border-radius: var(--r-md);
    box-shadow: var(--shadow);
    font-size: 13.5px;
  }
  h2 {
    margin: 0;
    font-size: 15px;
  }
  p {
    margin: 0;
  }
  .warn {
    color: var(--ink-soft);
  }
  label {
    display: flex;
    flex-direction: column;
    gap: var(--s1);
  }
  input {
    font: inherit;
    border: 1px solid var(--line);
    border-radius: var(--r-sm);
    padding: 0.3rem 0.5rem;
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
  button:disabled {
    opacity: 0.5;
    cursor: default;
  }
  .danger {
    color: var(--mark);
    border-color: var(--mark);
  }
</style>
