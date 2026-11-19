<script lang="ts">
  // A question block's controls (EXA-161). Nothing shows at rest. Hovering shows a ⋮⋮ handle
  // in the left gutter (a click opens the menu). Selecting the block (a click, keyboard
  // focus, or the caret in its text) shows a pill at its top-right edge: the main verb, Lock
  // and ⋯. The ⋯ menu also opens on a right-click, Shift+F10 or the ContextMenu key. The
  // block's shortcuts (shortcuts.ts) run the menu row that shows the same key.
  import { tick } from 'svelte'
  import Icon from '../Icon.svelte'
  import Menu, { type MenuItem } from '../Menu.svelte'
  import { menuGroups, pillActions, primaryRow, rowForShortcut, type QuestionAction, type QuestionFacts } from './questionMenu'
  import { blockShortcut, isTypingTarget, registerBlockKeys, BLOCK_KEYS } from './shortcuts'

  let {
    host,
    facts,
    number,
    selected = false,
    busy = false,
    marks,
    onMarks,
    summary = '',
    onAction,
  }: {
    /** The block's element: it gets the listeners, the `is-active` class and its name. */
    host: HTMLElement
    facts: QuestionFacts
    /** The printed question number (null while it isn't known). */
    number: number | null
    /** The editor's selection is on or in this block, and the editor has focus. */
    selected?: boolean
    busy?: boolean
    /** A free-form question's marks, edited in the pill (absent: no marks field). */
    marks?: number | null
    onMarks?: (marks: number | null) => void
    /** Status text in the pill, e.g. "2 parts · 5 marks". */
    summary?: string
    onAction: (action: QuestionAction) => void
  } = $props()

  let focusWithin = $state(false)
  let menuOpen = $state(false)
  let opening = $state(false) // the menu is being opened from outside the pill
  let menu: { openMenu: (at?: 'first' | 'last') => void } | undefined = $state()
  const active = $derived(focusWithin || selected || menuOpen || opening)
  const name = $derived(number === null ? 'this question' : `question ${number}`)

  const items = $derived<MenuItem[]>(
    menuGroups(facts).flatMap((group, g) =>
      group.map((row, i) => ({
        label: row.label,
        icon: row.icon,
        shortcut: row.shortcut,
        hint: row.hint,
        danger: row.danger,
        separator: g > 0 && i === 0,
        onSelect: () => onAction(row.action),
      })),
    ),
  )
  const pill = $derived(pillActions(facts))
  const primary = $derived(primaryRow(facts))

  export async function openMenu() {
    opening = true
    await tick() // the pill (and its menu) mount
    menu?.openMenu()
    opening = false
  }

  /** A key on this block (focused, or selected while the editor has focus). */
  function handleKey(e: KeyboardEvent, inText: boolean): boolean {
    const key = blockShortcut(e, inText)
    if (!key) return false
    if (key === 'menu') {
      e.preventDefault()
      void openMenu()
      return true
    }
    const row = rowForShortcut(facts, key)
    if (!row || (busy && row.action !== 'delete')) return false
    e.preventDefault()
    onAction(row.action)
    return true
  }

  function onKeydown(e: KeyboardEvent) {
    const t = e.target as HTMLElement
    // The open menu and anything typed in (marks, units) keep their own keys.
    if (isTypingTarget(t) || t.closest('[role="menu"]')) return
    if (handleKey(e, false)) e.stopPropagation()
  }

  function onContextMenu(e: MouseEvent) {
    if (isTypingTarget(e.target)) return // text keeps the browser's menu (spelling, paste)
    e.preventDefault()
    void openMenu()
  }

  const onFocusIn = () => (focusWithin = true)
  const onFocusOut = (e: FocusEvent) => (focusWithin = host.contains(e.relatedTarget as Node | null))

  $effect(() => {
    const el = host
    el.addEventListener('keydown', onKeydown)
    el.addEventListener('contextmenu', onContextMenu)
    el.addEventListener('focusin', onFocusIn)
    el.addEventListener('focusout', onFocusOut)
    const unregister = registerBlockKeys(el, handleKey)
    return () => {
      el.removeEventListener('keydown', onKeydown)
      el.removeEventListener('contextmenu', onContextMenu)
      el.removeEventListener('focusin', onFocusIn)
      el.removeEventListener('focusout', onFocusOut)
      unregister()
    }
  })

  $effect(() => {
    host.classList.toggle('is-active', active)
  })

  function marksInput(e: Event) {
    const raw = (e.currentTarget as HTMLInputElement).value
    if (raw.trim() === '') return onMarks?.(null)
    const n = Math.round(Number(raw))
    if (Number.isFinite(n)) onMarks?.(Math.min(100, Math.max(0, n)))
  }
</script>

<button
  type="button"
  class="qhandle"
  tabindex="-1"
  aria-label="Menu for {name}"
  title="Menu for {name}"
  onclick={() => void openMenu()}><Icon name="grip" /></button
>

{#if active}
  <div class="qpill" role="group" aria-label="Actions for {name}">
    {#if onMarks}
      <label class="marks">
        Marks
        <input
          type="number"
          min="0"
          max="100"
          value={marks ?? ''}
          aria-label="Marks"
          onchange={marksInput}
        />
      </label>
    {/if}
    {#if summary}<span class="summary">{summary}</span>{/if}
    {#each pill as control (control)}
      {#if control === 'primary' && primary}
        <button
          type="button"
          disabled={busy}
          title="{primary.label}{primary.shortcut ? ` (${primary.shortcut})` : ''}"
          onclick={() => onAction(primary.action)}
          ><Icon name="swap" /><span class="label">{primary.label}</span></button
        >
      {:else if control === 'addPart'}
        <button type="button" title="Add a lettered part" onclick={() => onAction('addPart')}
          ><Icon name="plus" /><span class="label">Part</span></button
        >
      {:else if control === 'lock'}
        <span class="sep" aria-hidden="true"></span>
        <button
          type="button"
          class="ico"
          aria-label="Lock"
          aria-pressed={facts.locked}
          title={facts.locked
            ? `Locked: kept when you regenerate. Unlock (${BLOCK_KEYS.lock})`
            : `Lock: keep it when you regenerate (${BLOCK_KEYS.lock})`}
          onclick={() => onAction('lock')}><Icon name={facts.locked ? 'lock' : 'unlock'} /></button
        >
      {/if}
    {/each}
    <Menu
      bind:this={menu}
      {items}
      label="More actions for {name}"
      menuLabel={number === null ? 'Question' : `Question ${number}`}
      align="end"
      triggerClass="ico"
      triggerTitle="More actions (Shift+F10)"
      onOpenChange={(open) => (menuOpen = open)}
    >
      {#snippet trigger()}<Icon name="more" />{/snippet}
    </Menu>
  </div>
{/if}

<style>
  .qhandle {
    position: absolute;
    left: -26px;
    top: 10px;
    width: 20px;
    height: 24px;
    display: grid;
    place-items: center;
    padding: 0;
    border: 0;
    border-radius: 4px;
    background: none;
    color: var(--ink-faint);
    cursor: pointer;
    opacity: 0;
  }
  :global(.qblock:hover) .qhandle,
  :global(.qblock.is-active) .qhandle {
    opacity: 1;
  }
  .qhandle:hover {
    background: var(--wash);
  }
  .qpill {
    position: absolute;
    right: 10px;
    top: -17px;
    z-index: 30;
    display: flex;
    align-items: center;
    gap: 2px;
    padding: 2px;
    background: var(--page);
    border: 1px solid var(--line);
    border-radius: 999px;
    box-shadow: var(--shadow);
    font-family: var(--sans);
    font-size: 12.5px;
    line-height: 1;
    white-space: nowrap;
  }
  .qpill button,
  .qpill :global(.ico) {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 28px;
    padding: 0 10px;
    border: 0;
    border-radius: 999px;
    background: none;
    color: var(--ink);
    font: inherit;
    font-weight: 600;
    cursor: pointer;
  }
  .qpill :global(.ico) {
    width: 28px;
    padding: 0;
    justify-content: center;
    color: var(--ink-soft);
  }
  .qpill button:hover:not(:disabled),
  .qpill :global(.ico:hover),
  .qpill :global(.ico[aria-expanded='true']) {
    background: var(--wash);
  }
  .qpill button[aria-pressed='true'] {
    background: var(--wash);
    color: var(--ink);
  }
  .qpill button:disabled {
    opacity: 0.5;
    cursor: default;
  }
  .sep {
    width: 1px;
    height: 16px;
    background: var(--line);
  }
  .marks {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 0 6px 0 10px;
    color: var(--ink-soft);
    font-weight: 600;
  }
  .marks input {
    width: 3.2rem;
    height: 24px;
    padding: 0 6px;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: var(--page);
    color: var(--ink);
    font: inherit;
    font-weight: 400;
  }
  .summary {
    padding: 0 8px 0 10px;
    color: var(--ink-soft);
  }
  /* the menu is the block's, not the page's text */
  .qpill :global(.popup) {
    font-family: var(--sans);
    line-height: 1.4;
  }
  @media (max-width: 640px) {
    .qhandle {
      display: none;
    }
    .qpill {
      right: 4px;
    }
    .qpill .label {
      display: none;
    }
  }
</style>
