<script lang="ts">
  // O2: "Move" on a paper row — a small menu of the folders and Unfiled. Keyboard: Enter/Space
  // or ArrowDown opens it on the current place, arrows/Home/End move, Escape or Tab closes.
  import { tick } from 'svelte'
  import type { Folder } from './docsApi'

  export let title: string
  export let folders: Folder[]
  export let current: string | null
  export let onMove: (folderId: string | null) => void

  let open = false
  let root: HTMLElement
  let trigger: HTMLButtonElement
  let menu: HTMLElement

  $: options = [
    ...folders.map((f) => ({ id: f.id as string | null, label: f.name })),
    { id: null as string | null, label: 'Unfiled' },
  ]

  const items = (): HTMLButtonElement[] =>
    menu ? Array.from(menu.querySelectorAll<HTMLButtonElement>('[role="menuitemradio"]')) : []

  async function show() {
    open = true
    await tick()
    const all = items()
    ;(all.find((b) => b.getAttribute('aria-checked') === 'true') ?? all[0])?.focus()
  }

  function close(refocus = true) {
    open = false
    if (refocus) trigger?.focus()
  }

  function choose(id: string | null) {
    close()
    if (id !== current) onMove(id)
  }

  function onTriggerKey(e: KeyboardEvent) {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      void show()
    }
  }

  function onMenuKey(e: KeyboardEvent) {
    const all = items()
    const i = all.indexOf(document.activeElement as HTMLButtonElement)
    let next: number | null = null
    if (e.key === 'ArrowDown') next = (i + 1) % all.length
    else if (e.key === 'ArrowUp') next = (i - 1 + all.length) % all.length
    else if (e.key === 'Home') next = 0
    else if (e.key === 'End') next = all.length - 1
    else if (e.key === 'Escape') {
      e.preventDefault()
      close()
      return
    } else if (e.key === 'Tab') {
      close(false)
      return
    }
    if (next !== null) {
      e.preventDefault()
      all[next]?.focus()
    }
  }

  function onWindowClick(e: MouseEvent) {
    if (open && root && !root.contains(e.target as Node)) close(false)
  }
</script>

<svelte:window on:click={onWindowClick} />

<div class="move" bind:this={root}>
  <button
    bind:this={trigger}
    class="trigger"
    aria-haspopup="menu"
    aria-expanded={open}
    aria-label={`Move “${title}” to a folder`}
    on:click={() => (open ? close() : void show())}
    on:keydown={onTriggerKey}
  >
    Move
  </button>
  {#if open}
    <div class="menu" role="menu" aria-label="Move to" tabindex="-1" bind:this={menu} on:keydown={onMenuKey}>
      {#each options as o (o.id ?? '')}
        <button
          role="menuitemradio"
          aria-checked={o.id === current}
          tabindex="-1"
          class:unfiled={o.id === null}
          on:click={() => choose(o.id)}
        >
          <span class="tick" aria-hidden="true">{o.id === current ? '✓' : ''}</span>{o.label}
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .move {
    position: relative;
  }
  .trigger {
    font: inherit;
    font-size: 12px;
    border: 1px solid var(--line);
    background: var(--paper);
    border-radius: 6px;
    padding: 0.25rem 0.6rem;
    color: var(--ink-soft);
    cursor: pointer;
  }
  .trigger[aria-expanded='true'] {
    border-color: var(--verify);
    color: var(--ink);
  }
  .menu {
    position: absolute;
    right: 0;
    top: calc(100% + 4px);
    z-index: 5;
    min-width: 12rem;
    max-height: 18rem;
    overflow-y: auto;
    display: grid;
    padding: 0.3rem;
    background: var(--page);
    border: 1px solid var(--line);
    border-radius: 10px;
    box-shadow: var(--shadow);
  }
  .menu button {
    font: inherit;
    font-size: 13px;
    text-align: left;
    border: 0;
    border-radius: 6px;
    background: transparent;
    color: var(--ink);
    padding: 0.4rem 0.6rem;
    cursor: pointer;
    display: flex;
    gap: 0.4rem;
    align-items: baseline;
  }
  .menu button:hover,
  .menu button:focus-visible {
    background: var(--wash);
    outline: none;
  }
  .menu button:focus-visible {
    box-shadow: inset 0 0 0 2px var(--verify);
  }
  .menu .unfiled {
    border-top: 1px solid var(--line-soft);
    border-radius: 0 0 6px 6px;
    color: var(--ink-soft);
  }
  .tick {
    width: 1em;
    color: var(--verify);
  }
</style>
