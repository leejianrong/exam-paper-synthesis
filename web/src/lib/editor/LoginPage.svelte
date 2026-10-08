<script lang="ts">
  // Sign in with Google, Microsoft or GitHub (no passwords). Providers come from the server,
  // so only the ones it is configured for appear.
  import { onMount } from 'svelte'
  import { loadProviders, loginUrl, type ProviderInfo } from '../session'

  export let error = ''

  let providers: ProviderInfo[] = []
  let loaded = false
  let failed = false

  const MESSAGES: Record<string, string> = {
    denied: 'Sign-in was cancelled.',
    state: 'That sign-in link expired. Please try again.',
    provider: 'The sign-in provider did not accept the request. Please try again.',
    not_configured: 'That sign-in method is not available.',
  }

  onMount(async () => {
    try {
      providers = (await loadProviders()).providers
    } catch {
      failed = true
    } finally {
      loaded = true
    }
  })
</script>

<main>
  <h1>Sign in</h1>
  <p class="lead">Sign in to write, keep and print your papers.</p>

  {#if error}<p class="error" role="alert">{MESSAGES[error] ?? 'Sign-in failed. Please try again.'}</p>{/if}

  {#if loaded && failed}
    <p class="error" role="alert">Cannot reach the server. Please try again shortly.</p>
  {:else if loaded && providers.length === 0}
    <p class="note">Sign-in is not set up on this server yet.</p>
  {/if}

  <div class="providers">
    {#each providers as p (p.name)}
      <a class="provider" href={loginUrl(p.name)}>Continue with {p.label}</a>
    {/each}
  </div>
</main>

<style>
  main {
    max-width: 24rem;
    margin: 6rem auto;
    padding: 0 1rem;
  }
  h1 {
    margin: 0 0 0.3rem;
    font-size: 1.6rem;
  }
  .lead {
    color: var(--ink-soft);
    margin: 0 0 1.4rem;
  }
  .providers {
    display: grid;
    gap: 0.6rem;
  }
  .provider {
    display: block;
    text-align: center;
    padding: 0.7rem 1rem;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--page);
    color: var(--ink);
    text-decoration: none;
    font-weight: 600;
  }
  .provider:hover {
    border-color: var(--verify);
    background: var(--verify-soft);
  }
  .error {
    color: var(--mark);
  }
  .note {
    color: var(--ink-faint);
  }
</style>
