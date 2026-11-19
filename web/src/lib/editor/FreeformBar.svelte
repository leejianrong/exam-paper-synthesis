<script lang="ts">
  // A free-form question's controls (EXA-161): the shared QuestionBar, fed through a store by
  // the ProseMirror node view (mounted once, so focus survives a change to the block).
  import type { Readable } from 'svelte/store'
  import QuestionBar from './QuestionBar.svelte'
  import type { QuestionAction, QuestionFacts } from './questionMenu'

  export let host: HTMLElement
  export let state: Readable<{
    facts: QuestionFacts
    number: number | null
    selected: boolean
    marks: number | null
    /** Single-part questions edit their marks in the pill; with parts it shows the total. */
    showMarks: boolean
    summary: string
  }>
  export let onAction: (action: QuestionAction) => void
  export let onMarks: (marks: number | null) => void
</script>

<QuestionBar
  {host}
  facts={$state.facts}
  number={$state.number}
  selected={$state.selected}
  marks={$state.marks}
  onMarks={$state.showMarks ? onMarks : undefined}
  summary={$state.summary}
  {onAction}
/>
