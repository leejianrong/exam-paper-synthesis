<script lang="ts">
  // Help > Keyboard shortcuts (Ctrl+/, EXA-163): every shortcut, grouped, as this computer's
  // keyboard shows it.
  import Dialog from '../Dialog.svelte'
  import { isMac, keyLabel } from '../keys'
  import { SHEET } from './shortcuts'

  let { onClose }: { onClose: () => void } = $props()
  const mac = isMac()
</script>

<Dialog title="Keyboard shortcuts" width="46rem" {onClose}>
  <div class="cols">
    {#each SHEET as g (g.group)}
      <section aria-labelledby="sheet-{g.group}">
        <h3 id="sheet-{g.group}">{g.group}</h3>
        <dl>
          {#each g.rows as r (r.label)}
            <div class="row">
              <dt>{r.label}</dt>
              <dd>{#each r.keys as k, i (k)}{#if i > 0}<span class="or">&nbsp;or&nbsp;</span>{/if}<kbd>{keyLabel(k, mac)}</kbd>{/each}</dd>
            </div>
          {/each}
        </dl>
      </section>
    {/each}
  </div>
  <p class="note">
    Question keys work on a selected question. {mac ? '⌘' : 'Ctrl'} shortcuts work anywhere in the paper.
  </p>
</Dialog>

<style>
  .cols {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
    gap: var(--s4);
  }
  h3 {
    margin: 0 0 var(--s2);
    font-size: 13px;
    color: var(--ink-soft);
  }
  dl {
    margin: 0;
  }
  .row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--s2);
    padding: 4px 0;
    border-bottom: 1px solid var(--line-soft);
  }
  dt {
    color: var(--ink);
  }
  dd {
    margin: 0;
    white-space: nowrap;
  }
  kbd {
    display: inline-block;
    min-width: 1.4em;
    padding: 1px 6px;
    border: 1px solid var(--line);
    border-bottom-width: 2px;
    border-radius: 4px;
    background: var(--paper);
    font: inherit;
    font-size: 12px;
    text-align: center;
    color: var(--ink);
  }
  .or {
    font-size: 12px;
    color: var(--ink-soft);
  }
  .note {
    margin: var(--s4) 0 0;
    font-size: 12.5px;
    color: var(--ink-soft);
  }
</style>
