<script lang="ts">
  // One figure, whichever way it is drawn: the server-rendered types fetch their SVG from the
  // engine, the rest are drawn by the TypeScript mirror. Used for the stem, a part and MCQ options.
  import { isServerDiagram, renderDiagram, type DiagramSpec } from './barModel'
  import ServerDiagram from './ServerDiagram.svelte'

  export let spec: DiagramSpec | null | undefined
  /** The tighter frame the editor body uses. */
  export let compact = false
  /** A generated question's figure: a bar model there is the worked solution (it carries
   *  "1 unit = …" and can show the answer), so the paper prints it in the key only (EXA-132). */
  export let keyOnly = false
  $: worked = keyOnly && (spec?.type === 'bar_model' || spec?.type === 'bar_model_before_after')
  $: svg = renderDiagram(spec)
  // Accessible label reflects the diagram kind. Older ratio cards keep "bar model".
  $: aria =
    spec?.type === 'geometry_figure'
      ? 'geometry figure'
      : spec?.type === 'shaded_fraction'
        ? 'fraction diagram'
        : isServerDiagram(spec)
          ? 'figure'
          : 'bar model'
</script>

{#if isServerDiagram(spec)}
  <div class="diagram" class:compact aria-label={aria}><ServerDiagram {spec} /></div>
{:else if svg}
  <!-- svg is built by renderDiagram from esc()-escaped, engine-derived spec values — no
       untrusted HTML reaches this sink. -->
  <!-- eslint-disable-next-line svelte/no-at-html-tags -->
  <div class="diagram" class:compact aria-label={aria}>{@html svg}</div>
{/if}

<style>
  .worked-note {
    margin: 0.2rem 0 0.6rem;
    font-size: 12px;
    color: var(--ink-faint);
    font-style: italic;
  }
  .diagram {
    margin: 0 0 1rem;
    padding: 0.85rem 0.75rem 0.5rem;
    background: var(--paper, var(--page));
    border: 1px solid var(--line-soft);
    border-radius: 9px;
    overflow-x: auto;
  }
  .diagram.compact {
    margin: 0;
    padding: 0.5rem;
    background: var(--page);
    border-radius: 6px;
  }
  .diagram :global(svg) {
    max-width: 100%;
    height: auto;
  }
</style>
{#if worked && (svg || isServerDiagram(spec))}
  <p class="worked-note">Worked model: printed in the answer key only, not on the student paper.</p>
{/if}
