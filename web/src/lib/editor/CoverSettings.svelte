<script lang="ts">
  // The cover page's fields in the side panel (EXA-164): every field the inline cover form had.
  // Each change goes back as the attrs to set on the cover node.
  import { createEventDispatcher } from 'svelte'
  import { COVER_FIELDS, COVER_SWITCHES } from './pages'

  export let attrs: Record<string, unknown>
  /** A swap or regenerate is running: the fields wait. */
  export let disabled = false

  const dispatch = createEventDispatcher<{ change: Record<string, unknown>; done: void }>()
  const set = (a: Record<string, unknown>) => dispatch('change', a)

  function onKey(e: KeyboardEvent) {
    if (e.key === 'Escape' && !e.defaultPrevented) {
      e.preventDefault()
      dispatch('done')
    }
  }
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<fieldset class="settings" {disabled} on:keydown={onKey}>
  {#each COVER_FIELDS as f (f.key)}
    <label class="row">
      <span>{f.label}</span>
      <input
        maxlength={f.max}
        placeholder={f.placeholder}
        value={String(attrs[f.key] ?? '')}
        on:input={(e) => set({ [f.key]: f.key === 'date' ? e.currentTarget.value || null : e.currentTarget.value })}
      />
    </label>
  {/each}
  <label class="row">
    <span>Instructions</span>
    <textarea
      rows="4"
      maxlength="2000"
      placeholder="One per line (optional)"
      aria-describedby="cover-instructions-hint"
      value={String(attrs.instructions ?? '')}
      on:input={(e) => set({ instructions: e.currentTarget.value || null })}
    ></textarea>
  </label>
  <p class="hint" id="cover-instructions-hint">Write NOT in capitals to print it bold and underlined.</p>
  <label class="check">
    <input
      type="checkbox"
      checked={attrs.examiner_table !== false}
      on:change={(e) => set({ examiner_table: e.currentTarget.checked })}
    />
    <span>For examiner's use table</span>
  </label>
  {#each COVER_SWITCHES as sw (sw.key)}
    <label class="check">
      <input
        type="checkbox"
        checked={attrs[sw.key] === true}
        on:change={(e) => set({ [sw.key]: e.currentTarget.checked })}
      />
      <span>{sw.label}</span>
    </label>
  {/each}
  <p class="hint">
    Time, question count, total marks, the examiner’s table and the page count come from the paper.
    The cover replaces the paper’s header and is left out of the answer key.
  </p>
</fieldset>
