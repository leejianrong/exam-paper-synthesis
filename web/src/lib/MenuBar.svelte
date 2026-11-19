<script lang="ts" module>
  import type { MenuItem } from './Menu.svelte'

  export interface BarMenu {
    label: string
    items: MenuItem[]
  }
</script>

<script lang="ts">
  // The editor's Paper / Insert / View / Help row (EXA-163), the WAI-ARIA menubar pattern: one
  // Tab stop (the last menu used), ←/→ move between menus and, while one is open, open the next
  // one instead; ↓, Enter or Space open; Esc closes and gives focus back to the menu's name.
  // Moving the pointer onto another name while a menu is open opens that one. Narrow windows
  // (`compact`) fold the row into a single "Menu" button with every row, menu by menu.
  import Menu from './Menu.svelte'

  let { menus, compact = false }: { menus: BarMenu[]; compact?: boolean } = $props()

  let active = $state(0)
  let openAt = $state(-1)
  const refs: Array<{ openMenu: (at?: 'first' | 'last') => void; focusTrigger: () => void } | undefined> = $state([])

  function side(i: number, dir: 1 | -1, wasOpen: boolean) {
    const n = menus.length
    const next = (i + dir + n) % n
    active = next
    if (wasOpen) refs[next]?.openMenu('first')
    else refs[next]?.focusTrigger()
  }

  function enter(i: number) {
    if (openAt >= 0 && openAt !== i) {
      active = i
      refs[i]?.openMenu('first')
    }
  }

  const folded = $derived<MenuItem[]>(
    menus.flatMap((m, g) => m.items.map((item, i) => ({ ...item, separator: i === 0 ? g > 0 : item.separator }))),
  )
</script>

{#if compact}
  <Menu items={folded} label="Menu" triggerClass="mb-trigger">
    {#snippet trigger()}Menu{/snippet}
  </Menu>
{:else}
  <div class="menubar" role="menubar" aria-label="Paper menus">
    {#each menus as m, i (m.label)}
      <Menu
        bind:this={refs[i]}
        items={m.items}
        menuLabel={m.label}
        triggerClass="mb-trigger"
        triggerRole="menuitem"
        triggerTabindex={i === active ? 0 : -1}
        onSide={(dir, wasOpen) => side(i, dir, wasOpen)}
        onTriggerEnter={() => enter(i)}
        onOpenChange={(o) => {
          if (o) {
            openAt = i
            active = i
          } else if (openAt === i) openAt = -1
        }}
      >
        {#snippet trigger()}{m.label}{/snippet}
      </Menu>
    {/each}
  </div>
{/if}

<style>
  .menubar {
    display: flex;
    gap: 2px;
    margin-left: -6px;
  }
  :global(.mb-trigger) {
    height: 24px;
    padding: 0 6px;
    border: 0;
    border-radius: 4px;
    background: none;
    color: var(--ink-soft);
    font: inherit;
    font-size: 13px;
    cursor: pointer;
  }
  :global(.mb-trigger:hover),
  :global(.mb-trigger[aria-expanded='true']) {
    background: var(--wash);
    color: var(--ink);
  }
</style>
