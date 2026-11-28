<script lang="ts" module>
  import type { IconName } from './Icon.svelte'

  /** One row of a menu. `separator` draws a rule above it (a new group). */
  export interface MenuItem {
    label: string
    onSelect: () => void
    icon?: IconName
    /** Shown right-aligned, e.g. "Ctrl+M". */
    shortcut?: string
    disabled?: boolean
    /** Why it is disabled, or what it does: the row's tooltip and description. */
    hint?: string
    /** A short line printed under the label, e.g. why the row is disabled (EXA-168). */
    note?: string
    danger?: boolean
    separator?: boolean
    /** An on/off row (e.g. "Show side panel"): a menuitemcheckbox with a tick when on. */
    checked?: boolean
  }
</script>

<script lang="ts">
  // A menu button (WAI-ARIA APG "menu button" pattern, EXA-160). The trigger opens a list of
  // actions: arrows move (wrapping), Home/End jump, a letter jumps to the next item starting
  // with it, Enter/Space choose, Esc closes and gives focus back to the trigger, Tab closes.
  // Opening focuses the first item (ArrowUp: the last). Choosing an item closes the menu and
  // returns focus to the trigger before the action runs, so an action may move focus itself
  // (e.g. back into the paper). Reused by the editor header, toolbar, block menus and, as one
  // menu of a menubar (MenuBar.svelte, EXA-163), by the Paper / Insert / View / Help menus.
  // Shortcuts are written the PC way and shown the Mac way on a Mac (keys.ts).
  import { tick, type Snippet } from 'svelte'
  import Icon from './Icon.svelte'
  import { ariaKeys, isMac, keyLabel } from './keys'

  let {
    items,
    label,
    trigger,
    header,
    footer,
    align = 'start',
    triggerClass = '',
    triggerTitle,
    disabled = false,
    menuLabel,
    onOpenChange,
    triggerRole,
    triggerTabindex,
    onSide,
    onTriggerEnter,
  }: {
    items: MenuItem[]
    /** The trigger's accessible name when its content is an icon or not the whole story. */
    label?: string
    trigger: Snippet
    /** Text above the items (not focusable), e.g. who is signed in. */
    header?: Snippet
    /** Muted text below the items (not focusable), e.g. "24 exports left today". */
    footer?: Snippet
    align?: 'start' | 'end'
    triggerClass?: string
    triggerTitle?: string
    disabled?: boolean
    /** The menu's accessible name; defaults to the trigger's. */
    menuLabel?: string
    /** Told when the menu opens or closes (e.g. a block keeps its toolbar while it's open). */
    onOpenChange?: (open: boolean) => void
    /** In a menubar the trigger is itself a menuitem with a roving tabindex. */
    triggerRole?: 'menuitem'
    triggerTabindex?: number
    /** In a menubar: ←/→ pressed on the trigger (`open` false) or inside the open menu, which
     *  has closed by then (`open` true). */
    onSide?: (dir: 1 | -1, open: boolean) => void
    /** In a menubar: the pointer moved onto this trigger. */
    onTriggerEnter?: () => void
  } = $props()

  const mac = isMac()

  const uid = `menu-${Math.random().toString(36).slice(2, 9)}`
  let open = $state(false)
  let button: HTMLButtonElement | undefined = $state()
  let root: HTMLElement | undefined = $state()
  let rows: HTMLButtonElement[] = $state([])

  function focusItem(i: number) {
    const n = items.length
    if (!n) return
    rows[((i % n) + n) % n]?.focus()
  }

  function current(): number {
    return rows.findIndex((r) => r === document.activeElement)
  }

  async function show(at: 'first' | 'last') {
    open = true
    onOpenChange?.(true)
    await tick() // the rows mount
    focusItem(at === 'first' ? 0 : items.length - 1)
  }

  function close(refocus: boolean) {
    if (!open) return
    open = false
    onOpenChange?.(false)
    if (refocus) button?.focus()
  }

  /** Open from elsewhere: a right-click, Shift+F10 or a drag handle (EXA-161). */
  export function openMenu(at: 'first' | 'last' = 'first') {
    if (!open) void show(at)
  }

  export function focusTrigger() {
    button?.focus()
  }

  function onTriggerClick() {
    if (open) close(true)
    else void show('first')
  }

  function onTriggerKey(e: KeyboardEvent) {
    if (onSide && (e.key === 'ArrowLeft' || e.key === 'ArrowRight')) {
      e.preventDefault()
      onSide(e.key === 'ArrowRight' ? 1 : -1, false)
    } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      void show(e.key === 'ArrowDown' ? 'first' : 'last')
    }
  }

  function onMenuKey(e: KeyboardEvent) {
    const i = current()
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        focusItem(i + 1)
        break
      case 'ArrowUp':
        e.preventDefault()
        focusItem(i < 0 ? items.length - 1 : i - 1)
        break
      case 'Home':
        e.preventDefault()
        focusItem(0)
        break
      case 'End':
        e.preventDefault()
        focusItem(items.length - 1)
        break
      case 'Escape':
        e.preventDefault()
        e.stopPropagation()
        close(true)
        break
      case 'Tab':
        close(false)
        break
      case 'ArrowLeft':
      case 'ArrowRight':
        if (onSide) {
          e.preventDefault()
          close(false)
          onSide(e.key === 'ArrowRight' ? 1 : -1, true)
        }
        break
      default:
        if (e.key.length === 1 && /\S/.test(e.key) && !e.ctrlKey && !e.metaKey && !e.altKey) {
          const k = e.key.toLowerCase()
          for (let step = 1; step <= items.length; step++) {
            const j = (Math.max(i, 0) + step) % items.length
            if (items[j].label.toLowerCase().startsWith(k)) {
              focusItem(j)
              break
            }
          }
        }
    }
  }

  function choose(item: MenuItem) {
    if (item.disabled) return
    close(true)
    item.onSelect()
  }

  function onWindowPointer(e: PointerEvent) {
    if (open && root && !root.contains(e.target as Node)) close(false)
  }

  function onFocusOut(e: FocusEvent) {
    const next = e.relatedTarget as Node | null
    if (open && next && root && !root.contains(next)) close(false)
  }
</script>

<svelte:window onpointerdown={onWindowPointer} />

<div class="menu-root" bind:this={root} onfocusout={onFocusOut}>
  <button
    bind:this={button}
    type="button"
    class={triggerClass}
    id="{uid}-button"
    aria-haspopup="menu"
    aria-expanded={open}
    aria-controls={open ? uid : undefined}
    aria-label={label}
    title={triggerTitle}
    role={triggerRole}
    tabindex={triggerTabindex}
    {disabled}
    onclick={onTriggerClick}
    onpointerenter={onTriggerEnter}
    onkeydown={onTriggerKey}>{@render trigger()}</button
  >
  {#if open}
    <div class="popup" class:end={align === 'end'}>
      {#if header}<div class="head">{@render header()}</div>{/if}
      <div
        role="menu"
        id={uid}
        tabindex="-1"
        aria-label={menuLabel ?? label}
        aria-labelledby={menuLabel || label ? undefined : `${uid}-button`}
        onkeydown={onMenuKey}
      >
        {#each items as item, i (item.label)}
          {#if item.separator && i > 0}<div class="sep" role="separator"></div>{/if}
          <button
            bind:this={rows[i]}
            type="button"
            role={item.checked === undefined ? 'menuitem' : 'menuitemcheckbox'}
            aria-checked={item.checked === undefined ? undefined : item.checked}
            tabindex="-1"
            class:danger={item.danger}
            aria-disabled={item.disabled ? 'true' : undefined}
            title={item.hint}
            aria-keyshortcuts={item.shortcut ? ariaKeys(item.shortcut, mac) : undefined}
            onclick={() => choose(item)}
          >
            {#if item.checked !== undefined}<span class="tick">{#if item.checked}<Icon name="check" />{/if}</span
              >{:else if item.icon}<Icon name={item.icon} />{/if}
            {#if item.note}<span class="two"><span class="label">{item.label}</span><span class="note"
                  >{item.note}</span
                ></span
              >{:else}<span class="label">{item.label}</span>{/if}
            {#if item.shortcut}<span class="k" aria-hidden="true">{keyLabel(item.shortcut, mac)}</span>{/if}
          </button>
        {/each}
      </div>
      {#if footer}<div class="foot">{@render footer()}</div>{/if}
    </div>
  {/if}
</div>

<style>
  .menu-root {
    position: relative;
    display: inline-flex;
  }
  .popup {
    position: absolute;
    top: calc(100% + var(--s1));
    left: 0;
    z-index: 40;
    min-width: 15.5rem;
    /* a long menu (the folded menu row on a small screen) scrolls inside the window */
    max-height: calc(100vh - 7rem);
    overflow-y: auto;
    padding: var(--s1);
    background: var(--page);
    border: 1px solid var(--line);
    border-radius: var(--r-md);
    box-shadow: var(--shadow);
    font-size: 13.5px;
    font-weight: 400;
    color: var(--ink);
    text-align: left;
  }
  .popup.end {
    left: auto;
    right: 0;
  }
  [role='menu'] {
    display: flex;
    flex-direction: column;
    outline: none;
  }
  .popup [role^='menuitem'] {
    display: flex;
    align-items: center;
    gap: var(--s2);
    width: 100%;
    padding: 6px var(--s2);
    border: 0;
    border-radius: 4px;
    background: none;
    color: inherit;
    font: inherit;
    text-align: left;
    white-space: nowrap;
    cursor: pointer;
  }
  .popup [role^='menuitem']:hover,
  .popup [role^='menuitem']:focus {
    background: var(--wash);
    outline: none;
  }
  .popup [role^='menuitem']:focus-visible {
    box-shadow: inset 0 0 0 2px var(--verify);
  }
  .popup [role^='menuitem'] :global(.icon) {
    color: var(--ink-soft);
  }
  .popup [role^='menuitem'][aria-disabled='true'] {
    color: var(--ink-faint);
    cursor: default;
  }
  .popup [role='menuitem'].danger,
  .popup [role='menuitem'].danger :global(.icon) {
    color: var(--mark);
  }
  .tick {
    display: inline-flex;
    width: 16px;
    flex: none;
  }
  .two {
    display: flex;
    flex-direction: column;
  }
  .note {
    max-width: 16rem;
    white-space: normal;
    font-size: 12px;
    color: var(--ink-soft);
  }
  .k {
    margin-left: auto;
    padding-left: var(--s4);
    color: var(--ink-faint);
    font-size: 12px;
  }
  .sep {
    margin: var(--s1) 0;
    border-top: 1px solid var(--line-soft);
  }
  .head {
    padding: 6px var(--s2) var(--s2);
    margin-bottom: var(--s1);
    border-bottom: 1px solid var(--line-soft);
    font-size: 12.5px;
    color: var(--ink-soft);
  }
  .foot {
    margin-top: var(--s1);
    padding: 6px var(--s2) var(--s1);
    border-top: 1px solid var(--line-soft);
    font-size: 12px;
    color: var(--ink-faint);
  }
</style>
