<script>
  export let q
  $: part = q.question.parts[0]

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

  <p class="answer"><span class="label">Answer</span> {fmtAnswer(part.answer)}</p>
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
  .answer { margin: 0; font-size: 1.05rem; }
  .answer .label {
    color: var(--muted);
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-right: 0.4rem;
  }
</style>
