<script lang="ts">
  import ClassicPage from './ClassicPage.svelte'
  import DocumentList from './lib/editor/DocumentList.svelte'
  import EditorPage from './lib/editor/EditorPage.svelte'
  import LoginPage from './lib/editor/LoginPage.svelte'
  import { route } from './lib/router'
  import { loadSession, session } from './lib/session'
  import { onMount } from 'svelte'

  onMount(loadSession)
</script>

{#if $session.status === 'loading'}
  <p class="boot">Loading…</p>
{:else if $session.status === 'anon'}
  <LoginPage error={$route.name === 'login' ? $route.error : ''} />
{:else if $route.name === 'editor'}
  {#key $route.id}
    <EditorPage id={$route.id} />
  {/key}
{:else if $route.name === 'classic'}
  <ClassicPage />
{:else}
  <DocumentList />
{/if}

<style>
  .boot {
    text-align: center;
    color: var(--ink-faint);
    margin-top: 4rem;
  }
</style>
