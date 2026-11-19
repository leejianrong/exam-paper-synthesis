<script lang="ts">
  // The sign-in page (EXA-170): the product name, what it is for, and a button per sign-in
  // provider the server is configured for (no passwords). Each button follows its provider's
  // wording ("Sign in with Google") and carries its mark. With the local development stub on
  // (EXAM_DEV_AUTH=1) a clearly marked panel lets a developer in without signing in.
  import { onMount } from 'svelte'
  import ErrorNote from '../ErrorNote.svelte'
  import Icon from '../Icon.svelte'
  import { canRetry, errorText, signInErrorText } from '../errors'
  import { loadProviders, loadSession, loginUrl, type ProviderInfo } from '../session'
  import ProviderMark from './ProviderMark.svelte'

  /** The API's sign-in error code from `#/login?error=…`, or ''. */
  let { error = '' }: { error?: string } = $props()

  let providers = $state<ProviderInfo[]>([])
  let dev = $state(false)
  let loading = $state(true)
  let loadError = $state<unknown>(null)

  async function load(): Promise<void> {
    loading = true
    loadError = null
    try {
      const info = await loadProviders()
      providers = info.providers
      dev = info.dev
    } catch (e) {
      loadError = e
    } finally {
      loading = false
    }
  }

  onMount(load)
</script>

<main class="signin">
  <div class="card">
    <header>
      <span class="mark" aria-hidden="true"><Icon name="check" size={18} /></span>
      <h1>Exam papers</h1>
      <p class="lead">Singapore P5–P6 maths papers with answer keys you can trust.</p>
    </header>

    {#if error}<ErrorNote message={signInErrorText(error)} />{/if}

    <section aria-labelledby="signin-h">
      <h2 id="signin-h" class="visually-hidden">Sign in</h2>
      {#if loading}
        <div class="skel button" role="status"><span class="visually-hidden">Loading the ways to sign in…</span></div>
      {:else if loadError}
        <ErrorNote
          message={errorText(loadError, "Couldn't load the ways to sign in")}
          onRetry={canRetry(loadError) ? load : null}
        />
      {:else}
        {#if providers.length}
          <ul class="providers">
            {#each providers as p (p.name)}
              <li>
                <a class="provider" href={loginUrl(p.name)}>
                  <ProviderMark name={p.name} />
                  <span>Sign in with {p.label}</span>
                </a>
              </li>
            {/each}
          </ul>
        {:else if !dev}
          <p class="note">Sign-in isn't set up on this server yet.</p>
        {/if}

        {#if dev}
          <div class="dev">
            <p class="devtag">Development only</p>
            <p>This server lets anyone in without an account (<code>EXAM_DEV_AUTH=1</code>). Never turn it on in production.</p>
            <button type="button" class="devgo" onclick={() => void loadSession()}>Continue without signing in</button>
          </div>
        {/if}
      {/if}
    </section>
  </div>
</main>

<style>
  .signin {
    min-height: 100vh;
    display: grid;
    place-items: center;
    padding: var(--s8) var(--s4);
  }
  .card {
    width: 100%;
    max-width: 400px;
    padding: var(--s8);
    background: var(--page);
    border: 1px solid var(--line);
    border-radius: var(--r-md);
    box-shadow: var(--shadow);
  }
  header {
    margin-bottom: var(--s6);
  }
  .mark {
    width: 32px;
    height: 32px;
    border-radius: var(--r-sm);
    background: var(--verify);
    color: var(--on-accent);
    display: grid;
    place-items: center;
    margin-bottom: var(--s3);
  }
  h1 {
    margin: 0 0 var(--s1);
    font-size: 22px;
    line-height: 1.25;
  }
  .lead {
    margin: 0;
    color: var(--ink-soft);
    font-size: 15px;
  }
  .providers {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: var(--s3);
  }
  /* the light button every provider allows: white, a grey rule, dark text, the mark at the left */
  .provider {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--s3);
    min-height: 44px;
    padding: 0 var(--s4);
    border: 1px solid var(--line);
    border-radius: var(--r-sm);
    background: var(--page);
    color: var(--ink);
    font-size: 14px;
    font-weight: 600;
    text-decoration: none;
    transition: background-color 0.12s, border-color 0.12s;
  }
  .provider :global(svg) {
    flex: none;
  }
  .provider:hover {
    background: var(--wash);
    border-color: var(--ink-faint);
  }
  .skel.button {
    height: 44px;
    border-radius: var(--r-sm);
  }
  .note {
    margin: 0;
    color: var(--ink-soft);
  }
  /* the dev stub: dashed and labelled, so nobody takes it for a real way in */
  .dev {
    padding: var(--s3) var(--s4) var(--s4);
    border: 1px dashed var(--ink-faint);
    border-radius: var(--r-sm);
    background: var(--wash);
    font-size: 13px;
    color: var(--ink-soft);
  }
  .providers + .dev {
    margin-top: var(--s6);
  }
  .dev p {
    margin: 0 0 var(--s3);
  }
  .devtag {
    font-weight: 700;
    color: var(--ink);
  }
  code {
    font-family: var(--mono);
    font-weight: 600;
  }
  .devgo {
    height: 32px;
    padding: 0 var(--s3);
    border: 1px solid var(--line);
    border-radius: var(--r-sm);
    background: var(--page);
    color: var(--ink);
    font: inherit;
    font-weight: 600;
    cursor: pointer;
  }
  .devgo:hover {
    background: var(--desk);
  }
  @media (max-width: 480px) {
    .signin {
      place-items: start center;
      padding: var(--s6) var(--s4);
    }
    .card {
      padding: var(--s6) var(--s4);
    }
  }
</style>
