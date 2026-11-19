<script lang="ts" module>
  import type { Command } from './shortcuts'

  /** The commands whose label (or menu) holds every typed word, labels that match first. */
  export function filterCommands(commands: Command[], query: string): Command[] {
    const words = query.toLowerCase().split(/\s+/).filter(Boolean)
    if (!words.length) return commands
    const hit = (text: string) => words.every((w) => text.toLowerCase().includes(w))
    const byLabel = commands.filter((c) => hit(c.label))
    const byGroup = commands.filter((c) => !hit(c.label) && hit(`${c.label} ${c.group}`))
    return [...byLabel, ...byGroup]
  }
</script>

<script lang="ts">
  // The command palette (Ctrl+K, EXA-163): every menu row and the selected question's actions by
  // name. Typing filters, ↑/↓ choose, Enter runs, Esc closes. A combobox with a listbox; the
  // highlighted row is the input's aria-activedescendant, so focus never leaves the field.
  import Dialog from '../Dialog.svelte'
  import { isMac, keyLabel } from '../keys'

  let {
    commands,
    onRun,
    onClose,
  }: {
    commands: Command[]
    /** Run this command (the palette is closed first, focus back where it was). */
    onRun: (c: Command) => void
    onClose: () => void
  } = $props()

  const uid = `cmd-${Math.random().toString(36).slice(2, 9)}`
  const mac = isMac()
  let query = $state('')
  let at = $state(0)
  let list: HTMLElement | undefined = $state()
  const shown = $derived(filterCommands(commands, query))
  const current = $derived(shown[Math.min(at, shown.length - 1)])

  $effect(() => {
    void query
    at = 0
  })

  $effect(() => {
    const row = list?.querySelector(`#${uid}-${Math.min(at, shown.length - 1)}`)
    row?.scrollIntoView?.({ block: 'nearest' })
  })

  function onKey(e: KeyboardEvent) {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      const n = shown.length
      if (n) at = (Math.min(at, n - 1) + (e.key === 'ArrowDown' ? 1 : -1) + n) % n
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (current) onRun(current)
    }
  }
</script>

<Dialog title="Commands" hideTitle top width="34rem" {onClose}>
  <input
    class="q"
    type="text"
    role="combobox"
    aria-label="Find a command"
    aria-expanded="true"
    aria-controls="{uid}-list"
    aria-autocomplete="list"
    aria-activedescendant={current ? `${uid}-${shown.indexOf(current)}` : undefined}
    placeholder="Find a command…"
    autocomplete="off"
    spellcheck="false"
    bind:value={query}
    onkeydown={onKey}
  />
  <div class="list" role="listbox" id="{uid}-list" aria-label="Commands" bind:this={list}>
    {#each shown as c, i (`${c.group}/${c.label}`)}
      <!-- the field keeps focus and handles the keys; a click runs the row -->
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <div
        role="option"
        id="{uid}-{i}"
        tabindex="-1"
        aria-selected={c === current}
        onclick={() => onRun(c)}
        onpointermove={() => (at = i)}
      >
        <span class="label">{c.label}</span>
        <span class="group">{c.group}</span>
        {#if c.shortcut}<kbd>{keyLabel(c.shortcut, mac)}</kbd>{/if}
      </div>
    {:else}
      <p class="none">No command matches “{query}”.</p>
    {/each}
  </div>
</Dialog>

<style>
  .q {
    width: 100%;
    box-sizing: border-box;
    height: 38px;
    padding: 0 var(--s3);
    border: 1px solid var(--line);
    border-radius: var(--r-sm);
    font: inherit;
    font-size: 14px;
    color: var(--ink);
    background: var(--page);
  }
  .q:focus {
    outline: none;
    border-color: var(--verify);
    box-shadow: 0 0 0 3px var(--verify-soft);
  }
  .list {
    max-height: 22rem;
    overflow-y: auto;
    margin-top: var(--s2);
  }
  [role='option'] {
    display: flex;
    align-items: center;
    gap: var(--s2);
    padding: 7px var(--s2);
    border-radius: 4px;
    cursor: pointer;
  }
  [role='option'][aria-selected='true'] {
    background: var(--wash);
    box-shadow: inset 2px 0 0 var(--verify);
  }
  .group {
    color: var(--ink-faint);
    font-size: 12px;
  }
  kbd {
    margin-left: auto;
    font: inherit;
    font-size: 12px;
    color: var(--ink-faint);
  }
  .none {
    margin: var(--s2);
    color: var(--ink-soft);
  }
</style>
