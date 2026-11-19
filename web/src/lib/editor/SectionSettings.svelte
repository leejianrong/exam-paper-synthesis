<script lang="ts">
  // A section's settings in the side panel (EXA-164): every field the inline section form had
  // (title, instructions, mode, marks target, marks shown, marking margin), with its derived
  // range and marks on top. Each change goes back as the attrs to set on the section node.
  import { createEventDispatcher } from 'svelte'
  import type { SectionInfo, SectionMode, SectionPlacement } from './doc'
  import MarksShown from './MarksShown.svelte'
  import { MODE_LABELS, markingOn, sectionMarksNote, sectionSummary, targetState } from './sections'

  export let attrs: Record<string, unknown>
  export let info: SectionInfo | undefined = undefined
  export let paper: SectionPlacement

  const dispatch = createEventDispatcher<{ change: Record<string, unknown>; done: void }>()
  const set = (a: Record<string, unknown>) => dispatch('change', a)

  $: mode = (attrs.mode ?? null) as SectionMode | null
  $: state = targetState(info)

  function target(e: Event) {
    const raw = (e.currentTarget as HTMLInputElement).value
    set({ marks_target: raw === '' ? null : Math.max(0, Math.min(500, Math.round(+raw))) })
  }

  function onKey(e: KeyboardEvent) {
    if (e.key === 'Escape' && !e.defaultPrevented) {
      e.preventDefault()
      dispatch('done')
    }
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="settings" on:keydown={onKey}>
  <p class="summary" data-state={state}>{sectionSummary(info)}</p>
  <label class="row">
    <span>Title</span>
    <input
      maxlength="120"
      placeholder="e.g. Booklet A"
      value={String(attrs.title ?? '')}
      on:input={(e) => set({ title: e.currentTarget.value })}
    />
  </label>
  <label class="row">
    <span>Instructions</span>
    <textarea
      rows="3"
      maxlength="1000"
      placeholder="Instructions for students (optional)"
      value={String(attrs.instructions ?? '')}
      on:input={(e) => set({ instructions: e.currentTarget.value })}
    ></textarea>
  </label>
  <label class="row">
    <span>Mode</span>
    <select value={mode ?? ''} on:change={(e) => set({ mode: e.currentTarget.value || null })}>
      <option value="">No mode</option>
      {#each Object.entries(MODE_LABELS) as [value, label] (value)}
        <option {value}>{label}</option>
      {/each}
    </select>
  </label>
  <label class="row">
    <span>Marks target</span>
    <input
      class="num"
      type="number"
      min="0"
      max="500"
      value={attrs.marks_target ?? ''}
      on:input={target}
    />
  </label>
  <label class="row">
    <span>Marks shown</span>
    <MarksShown
      section
      value={String(attrs.marks_placement ?? '')}
      {mode}
      describedby="section-marks-hint"
      on:change={(e) => set({ marks_placement: (e.target as HTMLSelectElement).value || null })}
    />
  </label>
  <p class="hint" id="section-marks-hint">{sectionMarksNote(attrs, paper)}</p>

  <label class="check">
    <input
      type="checkbox"
      checked={markingOn(attrs)}
      on:change={(e) => set({ marking: e.currentTarget.checked })}
    />
    <span>Marking margin</span>
  </label>
  <p class="hint">A ruled strip beside each question: "Do not write in this space".</p>
</div>
