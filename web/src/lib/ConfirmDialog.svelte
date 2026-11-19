<script lang="ts">
  // An in-page confirmation for an action that replaces work (EXA-160): it names what will
  // happen, the confirm button says the action, Esc or Cancel backs out. Focus starts on the
  // confirm button and goes back where it was when the dialog closes.
  import { onDestroy, onMount } from 'svelte'

  let {
    title,
    body,
    confirmLabel,
    onConfirm,
    onCancel,
  }: {
    title: string
    body: string
    confirmLabel: string
    onConfirm: () => void
    onCancel: () => void
  } = $props()

  let go: HTMLButtonElement | undefined = $state()
  let dialog: HTMLElement | undefined = $state()
  const returnTo = document.activeElement as HTMLElement | null

  onMount(() => go?.focus())
  onDestroy(() => {
    if (returnTo?.isConnected) returnTo.focus()
  })

  function onKey(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      e.preventDefault()
      onCancel()
    } else if (e.key === 'Tab' && dialog) {
      // keep focus inside the two buttons
      const buttons = Array.from(dialog.querySelectorAll('button'))
      const i = buttons.indexOf(document.activeElement as HTMLButtonElement)
      e.preventDefault()
      buttons[(i + (e.shiftKey ? -1 : 1) + buttons.length) % buttons.length]?.focus()
    }
  }
</script>

<div class="backdrop" role="presentation" onclick={(e) => e.target === e.currentTarget && onCancel()}>
  <div
    bind:this={dialog}
    class="dialog"
    role="alertdialog"
    aria-modal="true"
    aria-labelledby="confirm-title"
    aria-describedby="confirm-body"
    tabindex="-1"
    onkeydown={onKey}
  >
    <h2 id="confirm-title">{title}</h2>
    <p id="confirm-body">{body}</p>
    <div class="row">
      <button bind:this={go} class="primary" onclick={onConfirm}>{confirmLabel}</button>
      <button onclick={onCancel}>Cancel</button>
    </div>
  </div>
</div>

<style>
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
    padding: var(--s4);
    background: var(--page);
    color: var(--ink);
    border: 1px solid var(--line);
    border-radius: var(--r-md);
    box-shadow: var(--shadow);
    font-size: 13.5px;
  }
  h2 {
    margin: 0 0 var(--s2);
    font-size: 15px;
  }
  p {
    margin: 0 0 var(--s4);
    color: var(--ink-soft);
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
  button:hover {
    background: var(--wash);
  }
  .primary {
    background: var(--verify);
    border-color: var(--verify);
    color: var(--on-accent);
  }
  .primary:hover {
    background: var(--verify-ink);
  }
</style>
