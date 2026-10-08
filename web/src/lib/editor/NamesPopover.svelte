<script lang="ts">
  // "Edit names" form (W1a tier-1 edit): fields are built from the blueprint's
  // cosmetic slots, so only names and curated items are ever editable here.
  import { createEventDispatcher, onMount } from 'svelte'
  import { getEditableSlots, type EditableSlot } from '../api'
  import type { Question } from '../types'

  export let q: Question
  export let busy = false

  const dispatch = createEventDispatcher<{
    apply: { changes: Record<string, string | string[]> }
    close: void
  }>()

  let slots: EditableSlot[] = []
  let values: Record<string, string[]> = {}
  let loadError = ''
  let loaded = false

  async function load() {
    try {
      slots = await getEditableSlots(q.blueprint_code)
      const params = q.parameters ?? {}
      for (const slot of slots) {
        const current = params[slot.key]
        values[slot.key] = Array.isArray(current) ? current.map(String) : [String(current ?? '')]
      }
      values = values
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e)
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

  function label(slot: EditableSlot, i: number): string {
    if (slot.role === 'item') return 'Item'
    return slot.count > 1 ? `Name ${i + 1}` : 'Name'
  }

  function submit() {
    const changes: Record<string, string | string[]> = {}
    for (const slot of slots) {
      const v = values[slot.key]
      changes[slot.key] = slot.count > 1 || Array.isArray(q.parameters?.[slot.key]) ? v : v[0]
    }
    dispatch('apply', { changes })
  }
</script>

<form class="names" on:submit|preventDefault={submit} aria-label="Edit names">
  {#if !loaded}
    <p class="hint">Loading…</p>
  {:else if loadError}
    <p class="error" role="alert">{loadError}</p>
  {:else if slots.length === 0}
    <p class="hint">Nothing to rename in this question.</p>
  {:else}
    {#each slots as slot (slot.key)}
      {#each values[slot.key] ?? [] as value, i (i)}
        <label class="row">
          <span>{label(slot, i)}</span>
          {#if slot.role === 'item'}
            <select on:change={(e) => setValue(slot.key, i, e.currentTarget.value)}>
              {#each slot.pool ?? [] as option (option)}
                <option value={option} selected={option === value}>{option}</option>
              {/each}
            </select>
          {:else}
            <input
              {value}
              maxlength={slot.max_length}
              required
              on:input={(e) => setValue(slot.key, i, e.currentTarget.value)}
            />
          {/if}
        </label>
      {/each}
    {/each}
    <p class="hint">Only the wording changes — the numbers and the answer stay the same.</p>
  {/if}
  <div class="actions">
    <button type="submit" disabled={busy || !loaded || slots.length === 0}>Apply</button>
    <button type="button" class="ghost" on:click={() => dispatch('close')}>Cancel</button>
  </div>
</form>

<style>
  .names {
    border: 1px solid var(--line);
    background: var(--paper-2);
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
    grid-template-columns: 5.5rem 1fr;
    align-items: center;
    gap: 0.5rem;
  }
  .row span {
    color: var(--ink-soft);
  }
  input,
  select {
    font: inherit;
    padding: 0.3rem 0.45rem;
    border: 1px solid var(--line);
    border-radius: 6px;
    background: var(--paper);
    color: var(--ink);
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
