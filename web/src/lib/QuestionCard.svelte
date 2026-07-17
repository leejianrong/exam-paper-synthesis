<script lang="ts">
  import { createEventDispatcher } from 'svelte'
  import { renderDiagram } from './barModel'
  import type { EditOp } from './api'
  import type { Answer, Question } from './types'

  export let q: Question
  export let busy = false
  export let added = false
  $: part = q.question.parts[0]
  $: steps = part.solution_steps ?? []
  $: scheme = part.marking_scheme ?? []
  $: svg = renderDiagram(part.diagram)
  // Accessible label reflects the diagram kind (a geometry figure is not a bar
  // model). Older ratio cards keep the "bar model" label.
  $: diagramAria =
    part.diagram?.type === 'geometry_figure'
      ? 'geometry figure'
      : part.diagram?.type === 'shaded_fraction'
        ? 'fraction diagram'
        : 'bar model'
  // Edit ops + Approve are frozen once the question is in the worksheet.
  $: editDisabled = busy || added

  const dispatch = createEventDispatcher<{
    edit: { op: EditOp }
    approve: { q: Question }
    discard: { id: string }
  }>()

  // Edit-op availability is driven by the engine's authoritative available_ops
  // (KAN-243): the API attaches it per question, so the UI no longer re-derives
  // op applicability (e.g. the old blueprint_code.startsWith('ratio') heuristic
  // for toggle-diagram). The server is still the real guard.
  $: ops = q.available_ops ?? []
  $: canRegenerate = ops.includes('regenerate')
  $: canEasier = ops.includes('make-easier')
  $: canHarder = ops.includes('make-harder')
  $: canDecimals = ops.includes('change-to-decimals')
  $: canToggleDiagram = ops.includes('toggle-diagram')
  $: diagramLabel = part.diagram ? 'Hide diagram' : 'Show diagram'

  let showKey = false

  function fmtAnswer(a: Answer | undefined): string {
    if (!a) return ''
    switch (a.type) {
      case 'quantity':
      case 'decimal':
      case 'integer': {
        const u = a.unit ?? ''
        if (u === '$') return `$${a.value}`
        return u ? `${a.value} ${u}` : `${a.value}`
      }
      case 'fraction':
        return `${a.numerator}/${a.denominator}`
      case 'ratio':
        return (a.parts ?? []).join(' : ')
      case 'set':
        return (a.values ?? []).join(', ')
      case 'text':
        return a.text ?? ''
      default:
        return JSON.stringify(a)
    }
  }
</script>

<article class="card">
  <header>
    <span class="badge {q.validation.status}">{q.validation.status}</span>
    <span class="meta">{q.blueprint_code} · seed {q.seed} · [{part.marks}]</span>
  </header>

  <p class="text">{part.text}</p>

  {#if svg}
    <!-- svg is built by renderDiagram from esc()-escaped, engine-derived spec
         values — no untrusted HTML reaches this sink. -->
    <!-- eslint-disable-next-line svelte/no-at-html-tags -->
    <div class="diagram" aria-label={diagramAria}>{@html svg}</div>
  {/if}

  <p class="answer"><span class="label">Answer</span> {fmtAnswer(part.answer)}</p>

  <div class="edit-row" role="group" aria-label="edit question">
    {#if canRegenerate}
      <button
        class="edit"
        on:click={() => dispatch('edit', { op: 'regenerate' })}
        disabled={editDisabled}
      >
        Regenerate
      </button>
    {/if}
    {#if canEasier}
      <button
        class="edit"
        on:click={() => dispatch('edit', { op: 'make-easier' })}
        disabled={editDisabled}
      >
        Make easier
      </button>
    {/if}
    {#if canHarder}
      <button
        class="edit"
        on:click={() => dispatch('edit', { op: 'make-harder' })}
        disabled={editDisabled}
      >
        Make harder
      </button>
    {/if}
    {#if canDecimals}
      <button
        class="edit"
        on:click={() => dispatch('edit', { op: 'change-to-decimals' })}
        disabled={editDisabled}
      >
        Change to decimals
      </button>
    {/if}
    {#if canToggleDiagram}
      <button
        class="edit"
        on:click={() => dispatch('edit', { op: 'toggle-diagram' })}
        disabled={editDisabled}
      >
        {diagramLabel}
      </button>
    {/if}
  </div>

  <div class="gate-row" role="group" aria-label="review question">
    {#if added}
      <span class="added" role="status">✓ Added to worksheet</span>
    {:else}
      <button class="approve" on:click={() => dispatch('approve', { q })} disabled={busy}>
        Approve
      </button>
    {/if}
    <button class="discard" on:click={() => dispatch('discard', { id: q.id })} disabled={busy}>
      Discard
    </button>
  </div>

  {#if steps.length}
    <section class="solution">
      <h3>Worked solution <span class="marks">[{part.marks}]</span></h3>
      <ol>
        {#each steps as s, i (i)}
          <li>{s.text}</li>
        {/each}
      </ol>
    </section>
  {/if}

  {#if scheme.length}
    <button class="key-toggle" on:click={() => (showKey = !showKey)}>
      {showKey ? 'Hide' : 'Show'} detailed answer key (M/A/B)
    </button>
    {#if showKey}
      <ul class="scheme">
        {#each scheme as m, i (i)}
          <li>
            <span class="mtag {m.type}">{m.type}</span>
            <span class="mmark">[{m.mark}]</span>
            {m.description}
          </li>
        {/each}
      </ul>
    {/if}
  {/if}
</article>

<style>
  .card {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 1rem 1.15rem;
    box-shadow: 0 1px 2px rgba(20, 30, 60, 0.04);
  }
  header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.6rem;
  }
  .badge {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
  }
  .badge.pass { color: var(--pass); background: var(--pass-bg); }
  .badge.fail { color: var(--fail); background: var(--fail-bg); }
  .meta { color: var(--muted); font-size: 0.82rem; }
  .text { margin: 0 0 0.7rem; line-height: 1.5; }
  .diagram {
    margin: 0 0 0.8rem;
    padding: 0.5rem;
    background: #fbfcfe;
    border: 1px solid var(--line);
    border-radius: 8px;
    overflow-x: auto;
  }
  .answer { margin: 0; font-size: 1.05rem; }
  .edit-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 0.9rem;
  }
  .edit {
    background: transparent;
    border: 1px solid var(--line);
    color: var(--accent);
    border-radius: 8px;
    padding: 0.4rem 0.75rem;
    font-size: 0.82rem;
    font-weight: 600;
    cursor: pointer;
  }
  .edit:disabled { opacity: 0.55; cursor: default; }
  .gate-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.6rem;
  }
  .approve {
    background: var(--pass, #1a7f52);
    border: 1px solid transparent;
    color: #fff;
    border-radius: 8px;
    padding: 0.4rem 0.9rem;
    font-size: 0.82rem;
    font-weight: 700;
    cursor: pointer;
  }
  .approve:disabled { opacity: 0.55; cursor: default; }
  .discard {
    background: transparent;
    border: 1px solid var(--line);
    color: var(--muted);
    border-radius: 8px;
    padding: 0.4rem 0.75rem;
    font-size: 0.82rem;
    font-weight: 600;
    cursor: pointer;
  }
  .discard:disabled { opacity: 0.55; cursor: default; }
  .added {
    color: var(--pass, #1a7f52);
    font-size: 0.82rem;
    font-weight: 700;
  }
  .answer .label {
    color: var(--muted);
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-right: 0.4rem;
  }
  .solution { margin: 0.9rem 0 0; }
  .solution h3 {
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--muted);
    margin: 0 0 0.4rem;
  }
  .solution .marks { color: var(--ink); font-weight: 600; }
  .solution ol { margin: 0; padding-left: 1.2rem; line-height: 1.55; }
  .solution li { margin-bottom: 0.15rem; }
  .key-toggle {
    margin-top: 0.9rem;
    background: transparent;
    border: 1px solid var(--line);
    color: var(--accent);
    border-radius: 8px;
    padding: 0.4rem 0.75rem;
    font-size: 0.82rem;
    font-weight: 600;
    cursor: pointer;
  }
  .scheme {
    list-style: none;
    margin: 0.6rem 0 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }
  .scheme li {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    font-size: 0.9rem;
    line-height: 1.4;
  }
  .mtag {
    flex: 0 0 auto;
    font-weight: 700;
    font-size: 0.72rem;
    width: 1.3rem;
    text-align: center;
    border-radius: 4px;
    padding: 0.05rem 0;
    color: #fff;
  }
  .mtag.M { background: #2f5fe0; }
  .mtag.A { background: #1a7f52; }
  .mtag.B { background: #8a5cc7; }
  .mmark { color: var(--muted); font-size: 0.82rem; }
</style>
