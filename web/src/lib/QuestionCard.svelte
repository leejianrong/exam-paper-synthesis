<script>
  import { renderDiagram } from './barModel.js'

  export let q
  $: part = q.question.parts[0]
  $: steps = part.solution_steps ?? []
  $: scheme = part.marking_scheme ?? []
  $: svg = renderDiagram(part.diagram)

  let showKey = false

  function fmtAnswer(a) {
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
        return a.parts.join(' : ')
      case 'set':
        return a.values.join(', ')
      case 'text':
        return a.text
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
    <div class="diagram" aria-label="bar model">{@html svg}</div>
  {/if}

  <p class="answer"><span class="label">Answer</span> {fmtAnswer(part.answer)}</p>

  {#if steps.length}
    <section class="solution">
      <h3>Worked solution <span class="marks">[{part.marks}]</span></h3>
      <ol>
        {#each steps as s}
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
        {#each scheme as m}
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
