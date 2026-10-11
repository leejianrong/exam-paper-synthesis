<script lang="ts">
  // What sits under a question on the paper: the blank working space (drawn to its real size,
  // with a drag handle and S/M/L/XL presets) and the "Ans: ____ unit [marks]" line. The engine
  // prints the same two things into the PDF (render.py), so the page is what the student gets.
  import {
    MAX_SPACE_MM,
    PX_PER_MM,
    SPACE_PRESETS,
    UNIT_CHOICES,
    clampSpaceMm,
    defaultSpaceMm,
    unitParts,
    type MarksPlacement,
  } from './layout'

  export let marks: number | null = null
  /** The block's own setting; null = the default for its marks. */
  export let spaceMm: number | null = null
  /** The unit to print: the block's override, else the answer's own. */
  export let unit: string | null = null
  export let label = ''
  export let placement: MarksPlacement = 'answer'
  export let editable = true
  export let onSpace: (mm: number | null) => void = () => {}
  export let onUnit: (unit: string) => void = () => {}

  $: mm = spaceMm ?? defaultSpaceMm(marks)
  $: parts = unitParts(unit)
  $: showMarks = marks !== null && placement !== 'question'
  $: presetValue = spaceMm === null ? 'default' : (SPACE_PRESETS.find((p) => p.mm === spaceMm)?.label ?? 'custom')

  let startY = 0
  let startMm = 0
  let dragging = false
  function down(e: PointerEvent) {
    dragging = true
    startY = e.clientY
    startMm = mm
    ;(e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId)
  }
  function move(e: PointerEvent) {
    if (dragging) onSpace(clampSpaceMm(startMm + (e.clientY - startY) / PX_PER_MM))
  }
  function up() {
    dragging = false
  }
  function key(e: KeyboardEvent) {
    const step = e.key === 'ArrowDown' ? 5 : e.key === 'ArrowUp' ? -5 : 0
    if (!step) return
    e.preventDefault()
    onSpace(clampSpaceMm(mm + step))
  }
  function pick(e: Event) {
    const v = (e.currentTarget as HTMLSelectElement).value
    if (v === 'default') onSpace(null)
    else if (v !== 'custom') onSpace(SPACE_PRESETS.find((p) => p.label === v)?.mm ?? null)
  }
</script>

<div class="area" data-testid="answer-area">
  <div class="space" style="height:{mm * PX_PER_MM}px" class:editable>
    {#if editable}
      <div class="tools">
        <label>
          Working space
          <select aria-label="Working space" value={presetValue} on:change={pick}>
            <option value="default">Default ({defaultSpaceMm(marks)} mm)</option>
            {#each SPACE_PRESETS as p (p.label)}<option value={p.label}>{p.label} ({p.mm} mm)</option>{/each}
            {#if presetValue === 'custom'}<option value="custom">Custom ({mm} mm)</option>{/if}
          </select>
        </label>
      </div>
      <div
        class="grip"
        role="slider"
        tabindex="0"
        aria-label="Working space height"
        aria-orientation="vertical"
        aria-valuemin="0"
        aria-valuemax={MAX_SPACE_MM}
        aria-valuenow={mm}
        aria-valuetext="{mm} mm"
        on:pointerdown={down}
        on:pointermove={move}
        on:pointerup={up}
        on:pointercancel={up}
        on:keydown={key}
      ></div>
    {/if}
  </div>
  <div class="line">
    <span class="ans">Ans:</span>
    {#if label}<span class="ans">({label})</span>{/if}
    {#if parts.before}<span>{parts.before}</span>{/if}
    <span class="blank"></span>
    {#if editable}
      <select class="unit" aria-label="Answer unit" value={unit ?? ''} on:change={(e) => onUnit(e.currentTarget.value)}>
        {#each UNIT_CHOICES as u (u.value)}<option value={u.value}>{u.value === '' ? 'no unit' : u.label}</option>{/each}
      </select>
    {:else if parts.after}
      <span>{parts.after}</span>
    {/if}
    {#if showMarks}<span class="marks">[{marks}]</span>{/if}
  </div>
</div>

<style>
  .area {
    margin-top: 0.5rem;
  }
  .space {
    position: relative;
    border: 1px dashed var(--line);
    border-radius: 3px;
    background: transparent;
  }
  .tools {
    position: absolute;
    top: 0.25rem;
    right: 0.4rem;
    font-size: 11.5px;
    color: var(--ink-soft);
    opacity: 0;
    transition: opacity 0.12s;
  }
  .space:hover .tools,
  .space:focus-within .tools {
    opacity: 1;
  }
  .tools select,
  .unit {
    font: inherit;
    font-size: 12px;
    border: 1px solid var(--line);
    border-radius: 5px;
    background: var(--paper);
    color: var(--ink);
  }
  .grip {
    position: absolute;
    left: 0;
    right: 0;
    bottom: -4px;
    height: 8px;
    cursor: ns-resize;
    touch-action: none;
  }
  .grip::after {
    content: '';
    position: absolute;
    left: 50%;
    bottom: 3px;
    width: 36px;
    height: 3px;
    margin-left: -18px;
    border-radius: 2px;
    background: var(--line);
  }
  .grip:hover::after,
  .grip:focus-visible::after {
    background: var(--ink-soft);
  }
  .line {
    display: flex;
    align-items: baseline;
    gap: 0.4rem;
    margin: 0.5rem 0 0.2rem;
    font-family: var(--serif);
  }
  .ans {
    font-weight: 600;
  }
  .blank {
    flex: 1 1 auto;
    min-width: 4rem;
    border-bottom: 1px solid var(--ink);
  }
  .marks {
    margin-left: 0.3rem;
    font-family: var(--mono);
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--mark);
    white-space: nowrap;
  }
</style>
