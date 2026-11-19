<script lang="ts">
  // An in-page confirmation for an action that replaces or destroys work (EXA-160): it names
  // what will happen, the confirm button says the action, Esc or Cancel backs out, Tab stays
  // inside. Focus starts on the confirm button (or on the field when a word must be typed to
  // confirm) and goes back where it was when the dialog closes: if that control is disabled or
  // inert for now (the action it started is still running), as soon as it can take focus again.
  import { onDestroy, onMount } from 'svelte'

  let {
    title,
    body,
    confirmLabel,
    onConfirm,
    onCancel,
    danger = false,
    confirmWord = '',
    busy = false,
    error = '',
  }: {
    title: string
    body: string
    confirmLabel: string
    onConfirm: () => void
    onCancel: () => void
    /** A destructive action: the confirm button is drawn as a warning. */
    danger?: boolean
    /** A word to type before the confirm button works (e.g. DELETE). */
    confirmWord?: string
    /** The action is running: nothing can be pressed and Esc does nothing. */
    busy?: boolean
    error?: string
  } = $props()

  let go: HTMLButtonElement | undefined = $state()
  let field: HTMLInputElement | undefined = $state()
  let dialog: HTMLElement | undefined = $state()
  let typed = $state('')
  const returnTo = document.activeElement as HTMLElement | null

  onMount(() => (confirmWord ? field : go)?.focus())
  onDestroy(() => restoreFocus(returnTo))

  const canFocus = (el: HTMLElement) =>
    el.isConnected && !(el as HTMLButtonElement).disabled && !el.closest('[inert]')

  /** Focus `el` now, or once it is enabled and no longer inert, unless focus has moved on. */
  function restoreFocus(el: HTMLElement | null) {
    if (!el?.isConnected) return
    if (canFocus(el)) return el.focus()
    const watch = new MutationObserver(() => {
      const active = document.activeElement
      if (!el.isConnected || (active && active !== document.body)) watch.disconnect()
      else if (canFocus(el)) {
        watch.disconnect()
        el.focus()
      }
    })
    watch.observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ['disabled', 'inert'] })
  }

  function onKey(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      e.preventDefault()
      if (!busy) onCancel()
    } else if (e.key === 'Tab' && dialog) {
      // keep focus inside the dialog's controls
      const stops = Array.from(dialog.querySelectorAll<HTMLElement>('input, button')).filter(
        (el) => !(el as HTMLButtonElement).disabled,
      )
      e.preventDefault()
      if (!stops.length) return
      const i = stops.indexOf(document.activeElement as HTMLElement)
      const next = i < 0 ? (e.shiftKey ? stops.length - 1 : 0) : i + (e.shiftKey ? -1 : 1)
      stops[(next + stops.length) % stops.length]?.focus()
    }
  }
</script>

<div class="backdrop" role="presentation" onclick={(e) => e.target === e.currentTarget && !busy && onCancel()}>
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
    {#if confirmWord}
      <label class="word">
        <span>Type <strong>{confirmWord}</strong> to confirm</span>
        <input bind:this={field} bind:value={typed} autocomplete="off" spellcheck="false" />
      </label>
    {/if}
    {#if error}<p class="error" role="alert">{error}</p>{/if}
    <div class="row">
      <button
        bind:this={go}
        class={danger ? 'danger' : 'primary'}
        disabled={busy || (!!confirmWord && typed !== confirmWord)}
        onclick={onConfirm}>{confirmLabel}</button
      >
      <button disabled={busy} onclick={onCancel}>Cancel</button>
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
  button:disabled {
    opacity: 0.5;
    cursor: default;
  }
  .danger {
    color: var(--mark);
    border-color: var(--mark);
  }
  .word {
    display: flex;
    flex-direction: column;
    gap: var(--s1);
    margin: 0 0 var(--s4);
  }
  input {
    font: inherit;
    border: 1px solid var(--line);
    border-radius: var(--r-sm);
    padding: 0.3rem 0.5rem;
  }
  .error {
    color: var(--mark);
    font-size: 12.5px;
  }
</style>
