<script lang="ts">
  // The presentational body of a question (no edit/approve chrome): verified badge,
  // marks, question text and diagram. Used by the editor's question block and the picker.
  import { renderDiagram } from '../barModel'
  import type { Question } from '../types'

  export let q: Question
  $: part = q.question.parts[0]
  $: svg = renderDiagram(part.diagram)
  $: diagramAria =
    part.diagram?.type === 'geometry_figure'
      ? 'geometry figure'
      : part.diagram?.type === 'shaded_fraction'
        ? 'fraction diagram'
        : 'bar model'
</script>

<div class="qbody">
  <div class="meta">
    <span class="badge {q.validation.status}"
      ><span class="dot" aria-hidden="true"></span>{q.validation.status === 'pass'
        ? 'engine-verified'
        : 'unverified'}</span
    >
    <span class="marks">[{part.marks}]</span>
  </div>
  <p class="text">{part.text}</p>
  {#if svg}
    <!-- svg is built by renderDiagram from esc()-escaped, engine-derived spec values. -->
    <!-- eslint-disable-next-line svelte/no-at-html-tags -->
    <div class="diagram" aria-label={diagramAria}>{@html svg}</div>
  {/if}
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
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.1rem 0.5rem;
    border-radius: 999px;
  }
  .badge .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
  }
  .badge.pass {
    color: var(--verify-ink);
    background: var(--verify-soft);
  }
  .badge.fail {
    color: var(--mark);
    background: var(--mark-soft);
  }
  .marks {
    color: var(--mark);
    font-weight: 600;
  }
  .text {
    font-family: var(--serif);
    font-size: 1.05rem;
    line-height: 1.5;
    margin: 0 0 0.5rem;
    color: var(--ink);
  }
  .diagram {
    background: var(--paper);
    border: 1px solid var(--line-soft);
    border-radius: 6px;
    padding: 0.5rem;
    overflow-x: auto;
  }
  .diagram :global(svg) {
    max-width: 100%;
    height: auto;
  }
</style>
