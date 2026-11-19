<script lang="ts">
  // Settings (O1, EXA-125): saved on the account, so they follow the teacher across devices.
  import { onMount } from 'svelte'
  import ErrorNote from './ErrorNote.svelte'
  import { canRetry, errorText } from './errors'
  import { loadSettings, settings, updateSettings, type AnswerKeyStyle } from './settings'

  let busy = false
  let error = ''
  let retry: (() => void) | null = null
  let saved = ''

  onMount(() => {
    if ($settings === null) void loadSettings()
  })

  async function save(patch: Parameters<typeof updateSettings>[0], done: string) {
    busy = true
    error = ''
    retry = null
    saved = ''
    try {
      await updateSettings(patch)
      saved = done
    } catch (e) {
      error = errorText(e, "The setting wasn't saved")
      retry = canRetry(e) ? () => void save(patch, done) : null
    } finally {
      busy = false
    }
  }

  const toggleClassic = (on: boolean) =>
    save({ classic_generator: on }, on ? 'The Classic generator is on.' : 'The Classic generator is hidden.')

  const KEY_STYLES: { value: AnswerKeyStyle; label: string }[] = [
    { value: 'school', label: 'School key' },
    { value: 'worked', label: 'Worked solutions' },
  ]

  const setKeyStyle = (style: AnswerKeyStyle) =>
    save(
      { answer_key_style: style },
      style === 'school'
        ? 'New papers get the school key.'
        : 'New papers get worked solutions.',
    )
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
        <span id="set-key-style" class="name">Answer key style</span>
        <p class="desc">
          The answer key a new paper starts with. The school key gives the answers and short
          working only, as schools print it. Worked solutions repeat each question with its full
          solution and marking scheme. Papers you already have keep their own.
        </p>
      </div>
      <div class="seg" role="radiogroup" aria-labelledby="set-key-style">
        {#each KEY_STYLES as s (s.value)}
          <label class:on={$settings.answer_key_style === s.value}>
            <input
              type="radio"
              name="answer-key-style"
              value={s.value}
              checked={$settings.answer_key_style === s.value}
              disabled={busy}
              on:change={() => setKeyStyle(s.value)}
            />
            {s.label}
          </label>
        {/each}
      </div>
    </section>
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
  {#if error}<ErrorNote message={error} onRetry={retry} busy={busy} />{/if}
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
  .row + .row {
    margin-top: 0.75rem;
  }
  /* a two-way segmented control: radios styled as one pill */
  .seg {
    flex: none;
    display: inline-flex;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--wash);
    padding: 2px;
  }
  .seg label {
    position: relative;
    padding: 0.35rem 0.8rem;
    border-radius: 6px;
    font-size: 14px;
    color: var(--ink-soft);
    cursor: pointer;
    white-space: nowrap;
  }
  .seg label.on {
    background: var(--paper);
    color: var(--ink);
    font-weight: 600;
    box-shadow: 0 0 0 1px var(--line);
  }
  .seg input {
    position: absolute;
    opacity: 0;
    inset: 0;
    margin: 0;
    cursor: pointer;
  }
  .seg label:has(input:focus-visible) {
    outline: 3px solid var(--verify);
    outline-offset: 1px;
  }
  .seg label:has(input:disabled) {
    cursor: progress;
    opacity: 0.6;
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
  @media (max-width: 560px) {
    .row:has(.seg) {
      flex-wrap: wrap;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .switch,
    .switch::after {
      transition: none;
    }
  }
</style>
