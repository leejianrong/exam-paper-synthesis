<script lang="ts">
  // A question's data table (EXA-148), drawn as the printed paper draws it (render.py's
  // `content-table`): black 1px rules, centred cells, a bold caption. An `answer_for` cell is
  // the pupil's blank to fill in, so it shows empty here as on the student paper.
  import MathText from './MathText.svelte'
  import type { DataTableSpec, TableCell } from './types'

  export let table: DataTableSpec | null | undefined

  const text = (c: TableCell | undefined): string =>
    c === null || c === undefined || typeof c === 'object' ? '' : String(c)
</script>

{#if table}
  <table class="content-table">
    {#if table.caption}<caption><MathText text={table.caption} /></caption>{/if}
    {#if table.headers?.length}
      <thead>
        <tr>
          {#each table.headers as h, i (i)}<th><MathText text={text(h)} /></th>{/each}
        </tr>
      </thead>
    {/if}
    <tbody>
      {#each table.rows as row, r (r)}
        <tr>
          {#each row as cell, i (i)}<td><MathText text={text(cell)} /></td>{/each}
        </tr>
      {/each}
    </tbody>
  </table>
{/if}

<style>
  .content-table {
    border-collapse: collapse;
    margin: 0.4rem 0 0.6rem;
    font-family: var(--serif);
    color: var(--ink);
  }
  th,
  td {
    border: 1px solid var(--ink);
    padding: 0.3em 0.9em;
    text-align: center;
    min-width: 3.5em;
    height: 1.6em;
  }
  caption {
    font-weight: 600;
    margin-bottom: 0.3em;
  }
</style>
