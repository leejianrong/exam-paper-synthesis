<script lang="ts">
  // The app header (EXA-167): every screen but the editor, which has its own (EditorBar). The
  // product name, the two places (Papers, Question bank, plus Classic while that setting is on)
  // and the avatar menu, which holds Settings and the account.
  import AccountMenu from './editor/AccountMenu.svelte'
  import Icon from './Icon.svelte'
  import { route } from './router'
  import { settings } from './settings'

  const tabs = $derived([
    { name: 'list', label: 'Papers', href: '#/' },
    { name: 'bank', label: 'Question bank', href: '#/bank' },
    ...($settings?.classic_generator ? [{ name: 'classic', label: 'Classic', href: '#/classic' }] : []),
  ])
</script>

<header class="apphead">
  <span class="brand"><span class="mark" aria-hidden="true"><Icon name="check" size={12} /></span><span class="name">Examsmith</span></span>
  <nav aria-label="Main">
    {#each tabs as t (t.name)}
      <a href={t.href} aria-current={$route.name === t.name ? 'page' : undefined}>{t.label}</a>
    {/each}
  </nav>
  <div class="account"><AccountMenu /></div>
</header>

<style>
  .apphead {
    display: flex;
    align-items: center;
    gap: var(--s4);
    height: 52px;
    padding: 0 var(--s4);
    background: var(--page);
    border-bottom: 1px solid var(--line);
  }
  .brand {
    flex: none;
    display: flex;
    align-items: center;
    gap: var(--s2);
    font-size: 15px;
    font-weight: 700;
    white-space: nowrap;
  }
  .mark {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    background: var(--verify);
    color: var(--on-accent);
    display: grid;
    place-items: center;
  }
  nav {
    display: flex;
    gap: 2px;
    align-self: stretch;
    min-width: 0;
    /* on the narrowest phones the tabs scroll sideways inside the header, never the page */
    overflow-x: auto;
    scrollbar-width: none;
  }
  nav a {
    display: flex;
    align-items: center;
    padding: 0 10px;
    border-bottom: 2px solid transparent;
    color: var(--ink-soft);
    font-size: 13.5px;
    font-weight: 500;
    text-decoration: none;
    white-space: nowrap;
  }
  nav a:hover {
    color: var(--ink);
  }
  nav a[aria-current='page'] {
    color: var(--ink);
    font-weight: 600;
    border-bottom-color: var(--verify);
  }
  nav a:focus-visible {
    outline-offset: -2px;
  }
  .account {
    flex: none;
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: var(--s2);
  }
  @media (max-width: 600px) {
    .apphead {
      gap: var(--s2);
    }
    .brand .name {
      display: none;
    }
    nav a {
      padding: 0 6px;
    }
  }
</style>
