<script lang="ts">
  // Settings (O1, EXA-125): saved on the account, so they follow the teacher across devices.
  import { onMount } from 'svelte'
  import { loadSettings, settings, updateSettings } from './settings'

  let busy = false
  let error = ''
  let saved = ''

  onMount(() => {
    if ($settings === null) void loadSettings()
  })

  async function toggleClassic(on: boolean) {
    busy = true
    error = ''
    saved = ''
    try {
      await updateSettings({ classic_generator: on })
      saved = on ? 'The Classic generator is on.' : 'The Classic generator is hidden.'
    } catch (e) {
      error = e instanceof Error ? e.message : String(e)
    } finally {
      busy = false
    }
  }
</script>

<main>
  <a class="back" href="#/">← Your papers</a>
  <h1>Settings</h1>
  <p class="lede">Saved on your account, so they apply wherever you sign in.</p>

  {#if $settings === null}
    <p class="muted">Loading your settings…</p>
  {:else}
    <section class="row">
      <div class="text">
        <label for="set-classic" class="name">Show the Classic generator</label>
        <p class="desc">
          The original one-question-at-a-time generator with a worksheet tray. Papers and the editor
          don't need it; turn it on if you still use it.
        </p>
      </div>
      <input
        id="set-classic"
        type="checkbox"
        role="switch"
        class="switch"
        checked={$settings.classic_generator}
        disabled={busy}
        on:change={(e) => toggleClassic(e.currentTarget.checked)}
      />
    </section>
    {#if $settings.classic_generator}
      <p class="muted">Open it from <a href="#/classic">Classic generator</a> on Your papers.</p>
    {/if}
  {/if}
  <p class="status" role="status">{saved}</p>
  {#if error}<p class="error" role="alert">{error}</p>{/if}
</main>

<style>
  main {
    max-width: 720px;
    margin: 0 auto;
    padding: 2rem 1rem 4rem;
  }
  .back {
    font-size: 13px;
    color: var(--ink-faint);
  }
  h1 {
    font-family: var(--serif);
    margin: 0.6rem 0 0.2rem;
  }
  .lede,
  .muted {
    color: var(--ink-soft);
    margin: 0 0 1.4rem;
  }
  .row {
    display: flex;
    gap: 1.5rem;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 1.1rem;
    background: var(--paper);
    border: 1px solid var(--line);
    border-radius: 10px;
  }
  .name {
    font-weight: 600;
    color: var(--ink);
  }
  .desc {
    margin: 0.25rem 0 0;
    font-size: 14px;
    color: var(--ink-soft);
    max-width: 52ch;
  }
  /* An M3-style switch: a 52×32 track with a thumb that grows when on. */
  .switch {
    appearance: none;
    flex: none;
    position: relative;
    width: 52px;
    height: 32px;
    margin: 0;
    border-radius: 16px;
    border: 2px solid var(--ink-faint);
    background: var(--wash);
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s;
  }
  .switch::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 6px;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: var(--ink-faint);
    transform: translateY(-50%);
    transition: left 0.15s, width 0.15s, height 0.15s, background 0.15s;
  }
  .switch:checked {
    background: var(--verify);
    border-color: var(--verify);
  }
  .switch:checked::after {
    left: 24px;
    width: 24px;
    height: 24px;
    background: var(--paper);
  }
  .switch:focus-visible {
    outline: 3px solid var(--verify);
    outline-offset: 2px;
  }
  .switch:disabled {
    opacity: 0.6;
    cursor: progress;
  }
  .status {
    min-height: 1.2em;
    font-size: 13px;
    color: var(--ink-soft);
  }
  .error {
    color: var(--mark);
  }
  @media (prefers-reduced-motion: reduce) {
    .switch,
    .switch::after {
      transition: none;
    }
  }
</style>
