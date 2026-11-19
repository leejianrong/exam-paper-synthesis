<script lang="ts">
  // A modal dialog shell (EXA-163): the shortcut sheet, "What verified means", Move to folder and
  // the command palette. Esc or a click outside closes it, Tab stays inside, and focus goes back
  // to where it was when the dialog opened. The first field (or the first button) takes focus.
  import { onDestroy, onMount, type Snippet } from 'svelte'

  let {
    title,
    onClose,
    children,
    hideTitle = false,
    width = '30rem',
    top = false,
    returnFocus = true,
  }: {
    title: string
    onClose: () => void
    children: Snippet
    /** The title names the dialog for screen readers only, and there is no × (the palette). */
    hideTitle?: boolean
    width?: string
    /** Sit near the top of the window rather than in the middle (the palette). */
    top?: boolean
    /** Give focus back on close; false when the action that closed it moves focus itself. */
    returnFocus?: boolean
  } = $props()

  const uid = `dlg-${Math.random().toString(36).slice(2, 9)}`
  let box: HTMLElement | undefined = $state()
  const returnTo = document.activeElement as HTMLElement | null

  onMount(() => {
    const first = box?.querySelector<HTMLElement>('input, select, textarea, button:not(.x)')
    ;(first ?? box)?.focus()
  })
  onDestroy(() => {
    if (returnFocus && returnTo?.isConnected) returnTo.focus()
  })

  function onKey(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      e.preventDefault()
      e.stopPropagation()
      onClose()
    } else if (e.key === 'Tab' && box) {
      const stops = Array.from(box.querySelectorAll<HTMLElement>('input, select, textarea, button, a[href]')).filter(
        (el) => !(el as HTMLButtonElement).disabled,
      )
      if (!stops.length) return
      const i = stops.indexOf(document.activeElement as HTMLElement)
      if (e.shiftKey ? i <= 0 : i === stops.length - 1) {
        e.preventDefault()
        stops[e.shiftKey ? stops.length - 1 : 0].focus()
      }
    }
  }
</script>

<div class="backdrop" class:top role="presentation" onclick={(e) => e.target === e.currentTarget && onClose()}>
  <div
    bind:this={box}
    class="dialog"
    style:width="min({width}, calc(100vw - 2rem))"
    role="dialog"
    aria-modal="true"
    aria-labelledby="{uid}-title"
    tabindex="-1"
    onkeydown={onKey}
  >
    <div class="head" class:sr={hideTitle}>
      <h2 id="{uid}-title">{title}</h2>
      <!-- a hidden head keeps no × (Esc and a click outside close it): an invisible button
           would still be a Tab stop -->
      {#if !hideTitle}<button class="x" type="button" aria-label="Close" onclick={onClose}>×</button>{/if}
    </div>
    {@render children()}
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
  .backdrop.top {
    place-items: start center;
    padding-top: 12vh;
  }
  .dialog {
    max-height: 80vh;
    overflow: auto;
    padding: var(--s4);
    background: var(--page);
    color: var(--ink);
    border: 1px solid var(--line);
    border-radius: var(--r-md);
    box-shadow: var(--shadow);
    font-size: 13.5px;
    outline: none;
  }
  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: var(--s3);
  }
  h2 {
    margin: 0;
    font-size: 15px;
  }
  .x {
    width: 28px;
    height: 28px;
    border: 0;
    border-radius: var(--r-sm);
    background: none;
    color: var(--ink-soft);
    font-size: 18px;
    line-height: 1;
    cursor: pointer;
  }
  .x:hover {
    background: var(--wash);
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
