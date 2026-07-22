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
  // toggle-bar-view flips the before-after bar model's view_mode (KAN-310). The
  // button names the mode it switches TO; the current mode reads off the spec
  // (defaulting to "grouped").
  $: canToggleBarView = ops.includes('toggle-bar-view')
  $: barViewMode =
    part.diagram?.type === 'bar_model_before_after' ? (part.diagram.view_mode ?? 'grouped') : null
  $: barViewLabel = barViewMode === 'sliced' ? 'Group segments' : 'Slice into units'

  let showKey = false

  function fmtAnswer(a: Answer | undefined): string {
    if (!a) return ''
    switch (a.type) {
      case 'quantity':
      case 'decimal':
      case 'integer': {
        const u = a.unit ?? ''
        // Money renders at exactly 2 dp when it is a decimal amount
        // (change-to-decimals, KAN-309); integer money keeps its whole form.
        const shown = u === '$' && a.type === 'decimal' ? Number(a.value).toFixed(2) : `${a.value}`
        if (u === '$') return `$${shown}`
        return u ? `${shown} ${u}` : `${shown}`
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
    <span class="badge {q.validation.status}"><span class="dot" aria-hidden="true"></span
      >{q.validation.status}</span
    >
    <span class="meta"
      >{q.blueprint_code} · seed {q.seed} · <span class="marks">[{part.marks}]</span></span
    >
  </header>

  <p class="text">{part.text}</p>

  {#if svg}
    <!-- svg is built by renderDiagram from esc()-escaped, engine-derived spec
         values — no untrusted HTML reaches this sink. -->
    <!-- eslint-disable-next-line svelte/no-at-html-tags -->
    <div class="diagram" aria-label={diagramAria}>{@html svg}</div>
  {/if}

  <p class="answer">
    <span class="label">Answer</span> <span class="val">{fmtAnswer(part.answer)}</span>
  </p>

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
    {#if canToggleBarView}
      <button
        class="edit"
        on:click={() => dispatch('edit', { op: 'toggle-bar-view' })}
        disabled={editDisabled}
      >
        {barViewLabel}
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
    background: var(--paper-2);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 1.25rem 1.4rem;
    box-shadow: var(--shadow);
  }
  header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding-bottom: 0.8rem;
    border-bottom: 1px solid var(--line-soft);
    margin-bottom: 0.95rem;
  }
  /* validation badge = verify (mono, engine voice) */
  .badge {
    font-family: var(--mono);
    font-size: 10.5px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    padding: 0.2rem 0.55rem;
    border-radius: 5px;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .badge .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
    flex: none;
  }
  .badge.pass {
    color: var(--verify-ink);
    background: var(--verify-soft);
    border: 1px solid color-mix(in srgb, var(--verify) 30%, transparent);
  }
  .badge.fail {
    color: var(--mark);
    background: var(--mark-soft);
    border: 1px solid color-mix(in srgb, var(--mark) 30%, transparent);
  }
  /* engine data meta line = mono */
  .meta {
    font-family: var(--mono);
    color: var(--ink-faint);
    font-size: 12px;
    letter-spacing: -0.01em;
    margin-left: auto;
  }
  .meta .marks {
    color: var(--mark);
    font-weight: 600;
  }
  /* question stem = serif (the trusted paper) */
  .text {
    font-family: var(--serif);
    font-size: 1.24rem;
    line-height: 1.4;
    color: var(--ink);
    margin: 0 0 1rem;
    text-wrap: pretty;
  }
  .diagram {
    margin: 0 0 1rem;
    padding: 0.85rem 0.75rem 0.5rem;
    background: var(--paper);
    border: 1px solid var(--line-soft);
    border-radius: 9px;
    overflow-x: auto;
  }
  /* answer value = serif, in a verify-tinted box */
  .answer {
    display: flex;
    align-items: baseline;
    gap: 0.65rem;
    margin: 0;
    padding: 0.65rem 0.85rem;
    background: var(--verify-soft);
    border: 1px solid color-mix(in srgb, var(--verify) 22%, transparent);
    border-radius: 9px;
  }
  .answer .label {
    font-family: var(--mono);
    color: var(--verify-ink);
    font-size: 10.5px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }
  .answer .val {
    font-family: var(--serif);
    font-size: 1.3rem;
    font-weight: 600;
    color: var(--ink);
  }
  .edit-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 1rem;
  }
  /* controls = sans, quiet ghost buttons */
  .edit {
    background: transparent;
    border: 1px solid var(--line);
    color: var(--ink);
    border-radius: 8px;
    padding: 0.4rem 0.75rem;
    font-size: 0.82rem;
    font-weight: 500;
    font-family: var(--sans);
    cursor: pointer;
  }
  .edit:hover:not(:disabled) {
    background: var(--paper-sink);
  }
  .edit:disabled {
    opacity: 0.55;
    cursor: default;
  }
  .gate-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.65rem;
  }
  /* Approve = solid verify */
  .approve {
    background: var(--verify);
    border: 1px solid var(--verify);
    color: #fff;
    border-radius: 8px;
    padding: 0.4rem 0.95rem;
    font-size: 0.82rem;
    font-weight: 600;
    font-family: var(--sans);
    cursor: pointer;
  }
  .approve:disabled {
    opacity: 0.55;
    cursor: default;
  }
  .discard {
    background: transparent;
    border: 1px solid var(--line);
    color: var(--ink-faint);
    border-radius: 8px;
    padding: 0.4rem 0.75rem;
    font-size: 0.82rem;
    font-weight: 500;
    font-family: var(--sans);
    cursor: pointer;
  }
  .discard:disabled {
    opacity: 0.55;
    cursor: default;
  }
  .added {
    color: var(--verify-ink);
    font-size: 0.82rem;
    font-weight: 600;
  }
  .solution {
    margin: 1.15rem 0 0;
  }
  /* micro-label heading = mono uppercase */
  .solution h3 {
    font-family: var(--mono);
    font-size: 10.5px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--ink-faint);
    font-weight: 600;
    margin: 0 0 0.5rem;
  }
  .solution h3 .marks {
    color: var(--mark);
    font-weight: 600;
  }
  .solution ol {
    margin: 0;
    padding-left: 1.3rem;
    line-height: 1.5;
  }
  .solution li {
    margin-bottom: 0.25rem;
    font-size: 0.94rem;
  }
  .key-toggle {
    margin-top: 0.95rem;
    background: transparent;
    border: 1px solid var(--line);
    color: var(--ink);
    border-radius: 8px;
    padding: 0.4rem 0.75rem;
    font-size: 0.82rem;
    font-weight: 500;
    font-family: var(--sans);
    cursor: pointer;
  }
  .key-toggle:hover {
    background: var(--paper-sink);
  }
  .scheme {
    list-style: none;
    margin: 0.75rem 0 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
  }
  .scheme li {
    display: flex;
    align-items: baseline;
    gap: 0.65rem;
    font-size: 0.9rem;
    line-height: 1.4;
  }
  /* M/A/B tags = mono, outlined, semantic tokens (M=ink-soft, A=verify, B=u2) */
  .mtag {
    flex: 0 0 auto;
    font-family: var(--mono);
    font-weight: 600;
    font-size: 11px;
    width: 1.5rem;
    text-align: center;
    border-radius: 5px;
    padding: 2px 0;
    border: 1px solid currentColor;
  }
  .mtag.M {
    color: var(--ink-soft);
  }
  .mtag.A {
    color: var(--verify-ink);
  }
  .mtag.B {
    color: var(--u2);
  }
  .mmark {
    font-family: var(--mono);
    color: var(--mark);
    font-size: 12px;
    font-weight: 600;
  }
</style>
