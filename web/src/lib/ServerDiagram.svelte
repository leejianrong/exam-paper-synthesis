<script lang="ts" module>
  import { renderDiagramSvg } from './api'
  import type { ServerSpec } from './barModel'

  // One fetch per distinct spec for the life of the page; a failure is never cached.
  const cache: Record<string, Promise<string>> = {}

  function load(spec: ServerSpec): Promise<string> {
    const key = JSON.stringify(spec)
    if (!(key in cache)) {
      cache[key] = renderDiagramSvg(spec)
      cache[key].catch(() => delete cache[key])
    }
    return cache[key]
  }
</script>

<script lang="ts">
  // A figure the engine draws and the web has no mirror for (chart, solid, number_line,
  // panels): fetch the SVG from POST /render/diagram.
  export let spec: ServerSpec
</script>

{#await load(spec)}
  <p class="note" aria-busy="true">Drawing figure…</p>
{:then svg}
  <!-- svg is the engine's own deterministic render of a schema-validated spec. -->
  <!-- eslint-disable-next-line svelte/no-at-html-tags -->
  {@html svg}
{:catch}
  <p class="note" role="alert">The figure could not be drawn.</p>
{/await}

<style>
  .note {
    margin: 0;
    font-size: 0.85rem;
    color: var(--muted, #66708a);
  }
</style>
