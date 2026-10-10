<script lang="ts">
  // The options of a multiple-choice question: every option is question content (text and/or a
  // figure); which one is correct is the key, shown separately.
  import DiagramView from './DiagramView.svelte'
  import type { ChoiceOption } from './types'

  export let options: ChoiceOption[]
</script>

<ol class="options" aria-label="options">
  {#each options as o, i (i)}
    <li>
      <span class="tag">{o.label}</span>
      <div class="body">
        {#if o.text}<span class="otext">{o.text}</span>{/if}
        {#if o.diagram}<DiagramView spec={o.diagram} />{/if}
      </div>
    </li>
  {/each}
</ol>

<style>
  .options {
    list-style: none;
    margin: 0 0 1rem;
    padding: 0;
    display: grid;
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
  }
  .body {
    min-width: 0;
  }
  .body :global(.diagram) {
    margin: 0;
  }
</style>
