<script lang="ts">
  // The options of a multiple-choice question: every option is question content (text and/or a
  // figure); which one is correct is the key, shown separately. Text options sit in one column
  // "(1)" ... "(4)" under the stem, as the printed paper has them; picture options in a grid
  // (EXA-141).
  import DiagramView from './DiagramView.svelte'
  import MathText from './MathText.svelte'
  import type { ChoiceOption } from './types'

  export let options: ChoiceOption[]

  $: grid = options.some((o) => o.diagram)
</script>

<ol class="options" class:grid aria-label="options">
  {#each options as o, i (i)}
    <li>
      <span class="tag">({o.label})</span>
      <div class="body">
        {#if o.text}<span class="otext"><MathText text={o.text} /></span>{/if}
        {#if o.diagram}<DiagramView spec={o.diagram} />{/if}
      </div>
    </li>
  {/each}
</ol>

<style>
  .options {
    list-style: none;
    margin: 0 0 1rem;
    padding: 0 0 0 1.25rem;
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 0.45rem;
  }
  .options.grid {
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 0.6rem;
  }
  li {
    display: flex;
    gap: 0.5rem;
    align-items: flex-start;
  }
  .tag {
    font-weight: 600;
    color: var(--ink);
    min-width: 1.8rem;
  }
  .body {
    min-width: 0;
  }
  .body :global(.diagram) {
    margin: 0;
  }
</style>
