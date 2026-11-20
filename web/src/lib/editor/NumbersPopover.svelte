<script lang="ts">
  // "Edit numbers" form (EXA-89, tier-2 edit): one field per free number the blueprint marks
  // (a ratio or a list of scores is one row of small fields). The engine re-solves the
  // question, so the answer, working and key are never typed here; when it refuses, its
  // reason shows inline and the form stays open.
  import { errorText } from '../errors'
  import { createEventDispatcher, onMount } from 'svelte'
  import { getNumberSlots, type NumberSlot } from '../api'
  import type { Question } from '../types'
  import { formKeys } from './formKeys'

  export let q: Question
  export let busy = false
  /** Why the last Apply was refused (the engine's sentence), shown inline. */
  export let error = ''

  const dispatch = createEventDispatcher<{
    apply: { changes: Record<string, number | number[]> }
    close: void
  }>()

  let slots: NumberSlot[] = []
  let values: Record<string, string[]> = {}
  let loadError = ''
  let loaded = false

  $: answer = q.question.parts[0]?.answer
  $: answerText =
    answer && typeof answer.value === 'number'
      ? answer.unit === '$'
        ? `$${answer.value}`
        : `${answer.value}${answer.unit ? ` ${answer.unit}` : ''}`
      : ''

  async function load() {
    try {
      slots = await getNumberSlots(q.blueprint_code)
      const params = q.parameters ?? {}
      for (const slot of slots) {
        const current = params[slot.key]
        values[slot.key] = Array.isArray(current) ? current.map(String) : [String(current ?? '')]
      }
      values = values
    } catch (e) {
      loadError = errorText(e, "Couldn't load the numbers to edit")
    } finally {
      loaded = true
    }
  }
  onMount(() => {
    void load()
  })

  function setValue(key: string, i: number, v: string) {
    values[key][i] = v
  }

  function fieldLabel(slot: NumberSlot, i: number): string {
    return slot.list ? `${slot.label}, number ${i + 1}` : slot.label
  }

  function submit() {
    const changes: Record<string, number | number[]> = {}
    for (const slot of slots) {
      const v = values[slot.key].map(Number)
      changes[slot.key] = slot.list ? v : v[0]
    }
    dispatch('apply', { changes })
  }
</script>

<form
  class="numbers"
  on:submit|preventDefault={submit}
  aria-label="Edit numbers"
  use:formKeys={() => dispatch('close')}
>
  {#if !loaded}
    <p class="hint">Loading…</p>
  {:else if loadError}
    <p class="error" role="alert">{loadError}</p>
  {:else if slots.length === 0}
    <p class="hint">No numbers in this question can be changed.</p>
  {:else}
    {#each slots as slot (slot.key)}
      <div class="row">
        <span id="num-{slot.key}">{slot.label}</span>
        <div
          class="fields"
          role={slot.list ? 'group' : undefined}
          aria-labelledby={slot.list ? `num-${slot.key}` : undefined}
        >
          {#each values[slot.key] ?? [] as value, i (i)}
            {#if i > 0 && slot.sep}<span class="sep" aria-hidden="true">{slot.sep}</span>{/if}
            <input
              type="number"
              inputmode="numeric"
              step="1"
              min={slot.minimum}
              max={slot.maximum}
              required
              class:short={slot.list}
              aria-label={fieldLabel(slot, i)}
              {value}
              on:input={(e) => setValue(slot.key, i, e.currentTarget.value)}
            />
          {/each}
        </div>
      </div>
    {/each}
    {#if answerText}
      <div class="row derived">
        <span>Answer now</span>
        <output aria-label="Answer now, worked out by the engine">{answerText}</output>
      </div>
    {/if}
    {#if error}
      <p class="error" role="alert">{error}</p>
    {:else}
      <p class="hint">The engine works out the answer, the working and the key again.</p>
    {/if}
  {/if}
  <div class="actions">
    <button type="submit" disabled={busy || !loaded || slots.length === 0}>Apply</button>
    <button type="button" class="ghost" on:click={() => dispatch('close')}>Cancel</button>
  </div>
</form>

<style>
  .numbers {
    border: 1px solid var(--line);
    background: var(--wash);
    border-radius: 8px;
    padding: 0.7rem 0.8rem;
    margin: 0.4rem 0;
    display: grid;
    gap: 0.45rem;
    font-family: var(--sans);
    font-size: 13px;
  }
  .row {
    display: grid;
    grid-template-columns: 9.5rem 1fr;
    align-items: center;
    gap: 0.5rem;
  }
  .row > span {
    color: var(--ink-soft);
  }
  .fields {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.3rem;
  }
  .sep {
    color: var(--ink-soft);
  }
  input {
    font: inherit;
    width: 6.5rem;
    padding: 0.3rem 0.45rem;
    border: 1px solid var(--line);
    border-radius: 6px;
    background: var(--paper);
    color: var(--ink);
  }
  input.short {
    width: 3.6rem;
  }
  .derived output {
    color: var(--ink-faint);
  }
  .hint {
    margin: 0;
    color: var(--ink-faint);
    font-size: 12px;
  }
  .error {
    margin: 0;
    color: var(--mark);
  }
  .actions {
    display: flex;
    gap: 0.5rem;
  }
  button {
    font: inherit;
    border: 1px solid var(--verify);
    background: var(--verify);
    color: #fff;
    border-radius: 6px;
    padding: 0.3rem 0.8rem;
    cursor: pointer;
  }
  button.ghost {
    background: transparent;
    color: var(--ink);
    border-color: var(--line);
  }
  button:disabled {
    opacity: 0.5;
    cursor: default;
  }
</style>
