<script lang="ts">
  // The account avatar (EXA-160; was AccountChip): who you are, Settings, your data, sign out.
  // The local development stub has nothing to sign out of or export, so it gets Settings only.
  // Deleting the account confirms in a dialog that needs the word DELETE typed.
  import ConfirmDialog from '../ConfirmDialog.svelte'
  import Menu, { type MenuItem } from '../Menu.svelte'
  import { deleteAccount, exportAccountData, session, signOut } from '../session'

  let confirming = $state(false)
  let busy = $state(false)
  let downloading = $state(false)
  let error = $state('')

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
          {
            label: downloading ? 'Preparing download…' : 'Download my data',
            icon: 'download',
            hint: 'A zip of your papers, bank questions and images.',
            disabled: downloading,
            onSelect: download,
          },
          { label: 'Sign out', icon: 'signout', onSelect: () => void signOut() },
          { label: 'Delete my account…', icon: 'trash', danger: true, separator: true, onSelect: startDelete },
        ] satisfies MenuItem[]
      : []),
  ])

  function startDelete(): void {
    confirming = true
    error = ''
  }

  function cancel(): void {
    confirming = false
    error = ''
  }

  async function download(): Promise<void> {
    if (downloading) return
    downloading = true
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
      downloading = false
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
  <ConfirmDialog
    title="Delete your account?"
    body="This permanently deletes your account, all your papers, your question bank and your images. It cannot be undone. Download your data first if you want a copy."
    confirmLabel="Delete everything"
    confirmWord="DELETE"
    danger
    {busy}
    {error}
    onConfirm={erase}
    onCancel={cancel}
  />
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
</style>
