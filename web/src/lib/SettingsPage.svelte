<script lang="ts">
  // Settings (O1, EXA-125): saved on the account, so they follow the teacher across devices.
  import { onMount } from 'svelte'
  import ErrorNote from './ErrorNote.svelte'
  import { canRetry, errorText } from './errors'
  import MarksShown from './editor/MarksShown.svelte'
  import { MARKS_SHOWN, type MarksPlacement } from './editor/layout'
  import {
    loadSettings,
    settings,
    updateSettings,
    SCHOOL_NAME_MAX,
    type AnswerKeyStyle,
    type DefaultLevel,
  } from './settings'

  let saved = ''

  onMount(() => {
    if ($settings === null) void loadSettings()
  })

  // Saves run one at a time, in the order they were made (EXA-169): a later change never
  // overtakes an earlier one, and no control is disabled while one is in flight, so a click
  // that lands as the school name saves on blur is kept, not lost.
  let queue: Promise<unknown> = Promise.resolve()
  let pending = 0
  $: busy = pending > 0

  type Patch = Parameters<typeof updateSettings>[0]
  type Failure = { patch: Patch; done: string; onSaved?: () => void; message: string; retryable: boolean }
  // Unsaved changes, one per setting, oldest first. Only a later save of the same setting clears
  // its failure, so the alert stays while anything is unsaved, whatever else saves meanwhile.
  let failures = new Map<string, Failure>()
  $: failed = [...failures.values()]
  $: error = failed.map((f) => f.message).join(' ')
  $: retry = failed.some((f) => f.retryable) ? retryFailed : null

  const WHAT: Record<string, string> = {
    school_name: "The school name wasn't saved",
    default_level: "The level wasn't saved",
    marks_placement: "Marks shown wasn't saved",
    answer_key_style: "The answer key style wasn't saved",
  }

  /** Save a change; resolves true once stored. `onSaved` runs on success, also when the change
   *  is stored by Try again after a failure. */
  function save(patch: Patch, done: string, onSaved?: () => void): Promise<boolean> {
    const key = Object.keys(patch).join(',')
    const run = async (): Promise<boolean> => {
      saved = ''
      try {
        await updateSettings(patch)
        saved = done
        failures.delete(key)
        failures = failures
        onSaved?.()
        return true
      } catch (e) {
        failures.delete(key) // re-added last: the newest failure is retried last
        failures.set(key, {
          patch,
          done,
          onSaved,
          message: errorText(e, WHAT[key] ?? "The setting wasn't saved"),
          retryable: canRetry(e),
        })
        failures = failures
        return false
      }
    }
    pending += 1
    const next = queue.then(run).finally(() => (pending -= 1))
    queue = next
    return next
  }

  /** Try again: re-send every unsaved change that can be retried, in the order it was made. */
  function retryFailed() {
    for (const f of [...failures.values()]) if (f.retryable) void save(f.patch, f.done, f.onSaved)
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

  // EXA-169: the rest of what a new paper starts with. The API writes them into each paper it
  // makes, so they reach papers made from now on only.
  const LEVELS: { value: DefaultLevel; label: string }[] = [
    { value: '', label: 'Not set' },
    { value: 'P5', label: 'P5' },
    { value: 'P6', label: 'P6' },
  ]

  // The school name as typed; saved when the field is left (or on Enter). It follows the stored
  // value (a late load, a save) except while the teacher is in the field or has unsaved text.
  let school = ''
  let schoolFocused = false
  let schoolDirty = false
  $: if ($settings && !schoolFocused && !schoolDirty) school = $settings.school_name

  async function saveSchool() {
    if (!$settings) return
    const name = school.trim()
    if (name === $settings.school_name) {
      school = name
      schoolDirty = false
      return
    }
    await save(
      { school_name: name },
      name ? `New papers' covers will say ${name}.` : 'New papers have no school name.',
      () => {
        // stored (now or by Try again): show what was stored, unless typing went on since
        if (school.trim() === name) {
          schoolDirty = false
          school = $settings?.school_name ?? name
        }
      },
    )
  }

  const setLevel = (level: DefaultLevel) =>
    save(
      { default_level: level },
      level ? `New papers are ${level}.` : 'New papers have no level set.',
    )

  function setPlacement(e: Event) {
    const value = (e.currentTarget as HTMLSelectElement).value as MarksPlacement
    void save({ marks_placement: value }, `Marks shown on new papers: ${MARKS_SHOWN[value]}.`)
  }
</script>

<main>
  <h1>Settings</h1>
  <p class="lede">Saved on your account, so they apply wherever you sign in.</p>

  {#if $settings === null}
    <p class="muted">Loading your settings…</p>
  {:else}
    <h2 id="set-new-papers">New papers</h2>
    <p class="lede group-lede">
      What a new paper starts with. You can still change any of it in the paper itself.
    </p>
    <div role="group" aria-labelledby="set-new-papers">
      <section class="row">
        <div class="text">
          <label for="set-school" class="name">School name</label>
          <p class="desc" id="set-school-desc">
            Printed on the cover of papers you make from now on. Leave it empty to type it in each
            paper.
          </p>
        </div>
        <input
          id="set-school"
          class="text-input"
          type="text"
          maxlength={SCHOOL_NAME_MAX}
          autocomplete="organization"
          aria-describedby="set-school-desc"
          bind:value={school}
          on:input={() => (schoolDirty = true)}
          on:focus={() => (schoolFocused = true)}
          on:blur={() => (schoolFocused = false)}
          on:change={saveSchool}
        />
      </section>
      <section class="row">
        <div class="text">
          <span id="set-level" class="name">Level</span>
          <p class="desc">
            Stated on the cover of papers you make from now on, and the level the New dialog
            offers first. You can still generate at the other level.
          </p>
        </div>
        <div class="seg" role="radiogroup" aria-labelledby="set-level">
          {#each LEVELS as l (l.value)}
            <label class:on={$settings.default_level === l.value}>
              <input
                type="radio"
                name="default-level"
                value={l.value}
                checked={$settings.default_level === l.value}
                on:change={() => setLevel(l.value)}
              />
              {l.label}
            </label>
          {/each}
        </div>
      </section>
      <section class="row">
        <div class="text">
          <label for="set-marks" class="name">Marks shown</label>
          <p class="desc" id="set-marks-desc">
            Where each question's marks print on papers you make from now on. Sections follow this
            unless they set their own; multiple-choice and short-answer sections show marks in the
            section header.
          </p>
        </div>
        <MarksShown
          id="set-marks"
          describedby="set-marks-desc"
          value={$settings.marks_placement}
          on:change={setPlacement}
        />
      </section>
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
                on:change={() => setKeyStyle(s.value)}
              />
              {s.label}
            </label>
          {/each}
        </div>
      </section>
    </div>
    <h2>Classic generator</h2>
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
        on:change={(e) => toggleClassic(e.currentTarget.checked)}
      />
    </section>
    {#if $settings.classic_generator}
      <p class="muted">It's the <a href="#/classic">Classic</a> tab at the top of the page.</p>
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
  h1 {
    font-family: var(--serif);
    margin: 0.6rem 0 0.2rem;
  }
  h2 {
    font-size: 17px;
    margin: 2rem 0 0.3rem;
  }
  .group-lede {
    font-size: 14px;
    margin-bottom: 0.9rem;
  }
  .text-input,
  .row :global(select) {
    flex: none;
    width: 16rem;
    max-width: 100%;
    font: inherit;
    font-size: 14px;
    padding: 0.4rem 0.55rem;
    border: 1px solid var(--line);
    border-radius: 6px;
    background: var(--paper);
    color: var(--ink);
  }
  .text-input:focus-visible,
  .row :global(select:focus-visible) {
    outline: 3px solid var(--verify);
    outline-offset: 1px;
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
  .status {
    min-height: 1.2em;
    font-size: 13px;
    color: var(--ink-soft);
  }
  @media (max-width: 560px) {
    .row:has(.seg),
    .row:has(.text-input),
    .row:has(:global(select)) {
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
