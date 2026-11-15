<script lang="ts">
  import ClassicOff from './lib/ClassicOff.svelte'
  import ClassicPage from './ClassicPage.svelte'
  import DocumentList from './lib/editor/DocumentList.svelte'
  import EditorPage from './lib/editor/EditorPage.svelte'
  import LoginPage from './lib/editor/LoginPage.svelte'
  import SettingsPage from './lib/SettingsPage.svelte'
  import { route } from './lib/router'
  import { loadSession, session } from './lib/session'
  import { loadSettings, settings } from './lib/settings'
  import { onMount } from 'svelte'

  onMount(loadSession)
  // Settings belong to the signed-in teacher: load them once a session exists (O1).
  $: if ($session.status === 'user' && $settings === null) void loadSettings()
</script>

{#if $session.status === 'loading'}
  <p class="boot">Loading…</p>
{:else if $session.status === 'anon'}
  <LoginPage error={$route.name === 'login' ? $route.error : ''} />
{:else if $route.name === 'editor'}
  {#key $route.id}
    <EditorPage id={$route.id} />
  {/key}
{:else if $route.name === 'settings'}
  <SettingsPage />
{:else if $route.name === 'classic'}
  {#if $settings === null}
    <p class="boot">Loading…</p>
  {:else if $settings.classic_generator}
    <ClassicPage />
  {:else}
    <ClassicOff />
  {/if}
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
