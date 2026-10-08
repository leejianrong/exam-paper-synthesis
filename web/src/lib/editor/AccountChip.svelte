<script lang="ts">
  // Who you are, and sign out. Hidden for the local development stub (nothing to sign out of).
  import { session, signOut } from '../session'

  $: user = $session.status === 'user' ? $session.user : null
</script>

{#if user && !user.dev}
  <span class="chip">
    <span class="who" title={user.email ?? ''}>{user.name ?? user.email ?? 'Signed in'}</span>
    <button on:click={signOut}>Sign out</button>
  </span>
{/if}

<style>
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 13px;
    color: var(--ink-soft);
  }
  .who {
    max-width: 12rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  button {
    font: inherit;
    font-size: 12.5px;
    border: 1px solid var(--line);
    background: var(--paper);
    color: var(--ink);
    border-radius: 6px;
    padding: 0.2rem 0.6rem;
    cursor: pointer;
  }
</style>
