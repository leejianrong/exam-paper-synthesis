<script lang="ts">
  // The presentational body of a question (no edit/approve chrome): marks, question text and diagram. Used by the editor's question block and the picker.
  import ChoiceOptions from '../ChoiceOptions.svelte'
  import DiagramView from '../DiagramView.svelte'
  import type { Question } from '../types'

  export let q: Question
  $: part = q.question.parts[0]
</script>

<div class="qbody">
  <div class="meta">
    <span class="marks">[{part.marks}]</span>
  </div>
  {#if q.question.stem}<p class="text">{q.question.stem}</p>{/if}
  <DiagramView spec={q.question.diagram} />
  <p class="text">{part.text}</p>
  <DiagramView spec={part.diagram} />
  {#if part.answer?.type === 'choice'}<ChoiceOptions options={part.answer.options ?? []} />{/if}
</div>

<style>
  .meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.6rem;
    margin-bottom: 0.35rem;
    font-family: var(--mono);
    font-size: 11.5px;
  }
  .marks {
    color: var(--mark);
    font-weight: 600;
    margin-left: auto;
  }
  .text {
    font-family: var(--serif);
    font-size: 1.05rem;
    line-height: 1.5;
    margin: 0 0 0.5rem;
    color: var(--ink);
  }
</style>
