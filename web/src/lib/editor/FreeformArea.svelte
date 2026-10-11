<script lang="ts">
  // The free-form block's working space and Ans: line. Mounted once by the ProseMirror node
  // view and fed through a store, so a layout change updates it in place (a remount would
  // destroy the drag handle mid-drag and drop keyboard focus).
  import type { Readable } from 'svelte/store'
  import AnswerArea from './AnswerArea.svelte'
  import type { MarksPlacement } from './layout'

  export let state: Readable<{
    marks: number | null
    spaceMm: number | null
    unit: string | null
    placement: MarksPlacement
    label?: string
  }>
  export let onSpace: (mm: number | null) => void
  export let onUnit: (unit: string) => void
</script>

<AnswerArea
  marks={$state.marks}
  spaceMm={$state.spaceMm}
  unit={$state.unit}
  placement={$state.placement}
  label={$state.label ?? ''}
  {onSpace}
  {onUnit}
/>
