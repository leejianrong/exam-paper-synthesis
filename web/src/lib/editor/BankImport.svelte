<script lang="ts">
  // The bank import screen (W2c): choose .json files or paste JSON — one canonical object
  // or an array — and import into the owner's bank. Items arrive unreviewed; a duplicate id
  // is reported unless "Replace existing"; every item gets its own outcome and, when invalid,
  // the schema's path-pointed errors, so one bad item never blocks the rest.
  import { createEventDispatcher } from 'svelte'
  import { importBank, type ImportResult } from '../api'

  const dispatch = createEventDispatcher<{ done: { imported: number }; cancel: void }>()

  // The server caps a request at 200 objects / 2 MB; larger selections go in batches.
  const BATCH_OBJECTS = 200
  const BATCH_BYTES = 1_500_000

  interface Row extends ImportResult {
    source: string
  }

  let pasted = ''
  let files: File[] = []
  let replace = false
  let busy = false
  let error = ''
  let rows: Row[] = []
  let done = false

  function onFiles(e: Event) {
    files = Array.from((e.currentTarget as HTMLInputElement).files ?? [])
  }

  interface Item {
    source: string
    value: unknown
  }

  /** Parse one JSON document into items (an array is many; anything else is one). */
  function itemsOf(source: string, text: string): { items: Item[]; failure?: Row } {
    let parsed: unknown
    try {
      parsed = JSON.parse(text)
    } catch (e) {
      const why = e instanceof Error ? e.message : String(e)
      return {
        items: [],
        failure: { index: 0, id: null, status: 'invalid', errors: [`not valid JSON: ${why}`], source },
      }
    }
    const list = Array.isArray(parsed) ? parsed : [parsed]
    return {
      items: list.map((value, i) => ({ source: list.length > 1 ? `${source} #${i + 1}` : source, value })),
    }
  }

  function batches(items: Item[]): Item[][] {
    const out: Item[][] = []
    let cur: Item[] = []
    let bytes = 0
    for (const item of items) {
      const size = JSON.stringify(item.value ?? null).length
      if (cur.length && (cur.length >= BATCH_OBJECTS || bytes + size > BATCH_BYTES)) {
        out.push(cur)
        cur = []
        bytes = 0
      }
      cur.push(item)
      bytes += size
    }
    if (cur.length) out.push(cur)
    return out
  }

  $: canImport = !busy && (files.length > 0 || pasted.trim() !== '')

  async function run() {
    busy = true
    error = ''
    rows = []
    done = false
    try {
      const items: Item[] = []
      const failures: Row[] = []
      for (const file of files) {
        const { items: got, failure } = itemsOf(file.name, await file.text())
        items.push(...got)
        if (failure) failures.push(failure)
      }
      if (pasted.trim() !== '') {
        const { items: got, failure } = itemsOf('pasted JSON', pasted)
        items.push(...got)
        if (failure) failures.push(failure)
      }
      const out: Row[] = [...failures]
      let imported = 0
      for (const batch of batches(items)) {
        const res = await importBank(
          batch.map((b) => b.value),
          replace,
        )
        imported += res.imported + res.replaced
        for (const r of res.results) out.push({ ...r, source: batch[r.index]?.source ?? `#${r.index + 1}` })
      }
      rows = out
      done = true
      if (imported > 0) dispatch('done', { imported })
    } catch (e) {
      error = e instanceof Error ? e.message : String(e)
    } finally {
      busy = false
    }
  }

  const LABELS: Record<ImportResult['status'], string> = {
    imported: 'Imported',
    replaced: 'Replaced',
    duplicate: 'Already in your bank',
    invalid: 'Not imported',
  }
</script>

<section class="import" aria-label="Import questions">
  <p class="lead">
    Import canonical question JSON — one object or an array — into your bank. Imported
    questions start <b>unreviewed</b>.
  </p>

  <label class="field"
    ><span>JSON files</span>
    <input type="file" accept=".json,application/json" multiple on:change={onFiles} aria-label="Choose JSON files" />
  </label>
  <label class="field"
    ><span>Or paste JSON</span>
    <textarea rows="5" bind:value={pasted} spellcheck="false" aria-label="Paste JSON"></textarea>
  </label>
  <label class="check"
    ><input type="checkbox" bind:checked={replace} /> Replace existing questions with the same id</label
  >

  <div class="actions">
    <button class="go" disabled={!canImport} on:click={run}>{busy ? 'Importing…' : 'Import'}</button>
    <button on:click={() => dispatch('cancel')}>{done ? 'Back to bank' : 'Cancel'}</button>
  </div>

  {#if error}<p class="error" role="alert">{error}</p>{/if}

  {#if rows.length}
    <ul class="results" aria-label="Import results">
      {#each rows as r, i (i)}
        <li class="row {r.status}" data-status={r.status}>
          <span class="chip">{LABELS[r.status]}</span>
          <span class="src">{r.source}{r.id ? ` — ${r.id}` : ''}</span>
          {#if r.errors?.length}
            <ul class="errs">
              {#each r.errors as e, j (j)}<li>{e}</li>{/each}
            </ul>
          {/if}
        </li>
      {/each}
    </ul>
  {/if}
</section>

<style>
  .import {
    display: grid;
    gap: 0.7rem;
  }
  .lead {
    margin: 0;
    color: var(--ink-soft);
    font-size: 13.5px;
  }
  .field {
    display: grid;
    gap: 0.2rem;
    font-size: 12px;
    color: var(--ink-soft);
  }
  textarea {
    font-family: var(--mono);
    font-size: 12px;
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 0.4rem 0.5rem;
    background: var(--paper);
    color: var(--ink);
  }
  .check {
    display: flex;
    gap: 0.4rem;
    align-items: center;
    font-size: 13px;
    color: var(--ink);
  }
  .actions {
    display: flex;
    gap: 0.5rem;
  }
  button {
    font: inherit;
    border: 1px solid var(--line);
    background: var(--paper);
    color: var(--ink);
    border-radius: 6px;
    padding: 0.4rem 0.9rem;
    cursor: pointer;
  }
  .go {
    border-color: var(--verify);
    background: var(--verify);
    color: #fff;
  }
  button:disabled {
    opacity: 0.55;
    cursor: default;
  }
  .error {
    color: var(--mark);
    margin: 0;
    font-size: 13px;
  }
  .results {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 0.4rem;
  }
  .row {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.2rem 0.6rem;
    align-items: baseline;
    padding: 0.4rem 0.6rem;
    border: 1px solid var(--line);
    border-radius: 6px;
    background: var(--page);
    font-size: 13px;
  }
  .chip {
    font-family: var(--mono);
    font-size: 11.5px;
    padding: 0.1rem 0.5rem;
    border-radius: 999px;
    background: var(--verify-soft);
    color: var(--verify-ink);
  }
  .duplicate .chip {
    background: var(--paper-sink);
    color: var(--ink-soft);
  }
  .invalid .chip {
    background: var(--mark-soft);
    color: var(--mark);
  }
  .errs {
    grid-column: 2;
    margin: 0;
    padding-left: 1.1rem;
    color: var(--mark);
    font-family: var(--mono);
    font-size: 12px;
  }
</style>
