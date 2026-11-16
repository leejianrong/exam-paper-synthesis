<script lang="ts">
  // One figure. The engine draws every type (ServerDiagram fetches POST /render/diagram), so the
  // editor and the Classic page show the drawing the PDF prints (EXA-151). A raster is a picture
  // carried verbatim, shown as an <img>. Used for the stem, a part and MCQ options.
  import type { DiagramSpec } from './diagram'
  import ServerDiagram from './ServerDiagram.svelte'

  export let spec: DiagramSpec | null | undefined
  /** The tighter frame the editor body uses. */
  export let compact = false
  /** A generated question's figure: a bar model there is the worked solution (it carries
   *  "1 unit = …" and can show the answer), so the paper prints it in the key only (EXA-132). */
  export let keyOnly = false
  $: isBarModel = spec?.type === 'bar_model' || spec?.type === 'bar_model_before_after'
  $: worked = keyOnly && isBarModel
  // Accessible label reflects the diagram kind.
  $: aria =
    spec?.type === 'geometry_figure'
      ? 'geometry figure'
      : spec?.type === 'shaded_fraction'
        ? 'fraction diagram'
        : isBarModel
          ? 'bar model'
          : 'figure'
</script>

{#if spec?.type === 'raster'}
  <div class="diagram" class:compact aria-label={aria}>
    <img src={spec.asset_ref} alt={spec.alt_text ?? ''} />
  </div>
{:else if spec}
  <div class="diagram" class:compact aria-label={aria}><ServerDiagram {spec} /></div>
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
  .diagram :global(svg),
  .diagram img {
    max-width: 100%;
    height: auto;
  }
</style>
{#if worked}
  <p class="worked-note">Worked model: printed in the answer key only, not on the student paper.</p>
{/if}
