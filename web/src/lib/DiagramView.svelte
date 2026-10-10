<script lang="ts">
  // One figure, whichever way it is drawn: the server-rendered types fetch their SVG from the
  // engine, the rest are drawn by the TypeScript mirror. Used for the stem, a part and MCQ options.
  import { isServerDiagram, renderDiagram, type DiagramSpec } from './barModel'
  import ServerDiagram from './ServerDiagram.svelte'

  export let spec: DiagramSpec | null | undefined
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
  <div class="diagram" aria-label={aria}><ServerDiagram {spec} /></div>
{:else if svg}
  <!-- svg is built by renderDiagram from esc()-escaped, engine-derived spec values — no
       untrusted HTML reaches this sink. -->
  <!-- eslint-disable-next-line svelte/no-at-html-tags -->
  <div class="diagram" aria-label={aria}>{@html svg}</div>
{/if}

<style>
  .diagram {
    margin: 0 0 1rem;
    padding: 0.85rem 0.75rem 0.5rem;
    background: var(--paper, var(--page));
    border: 1px solid var(--line-soft);
    border-radius: 9px;
    overflow-x: auto;
  }
  .diagram :global(svg) {
    max-width: 100%;
    height: auto;
  }
</style>
