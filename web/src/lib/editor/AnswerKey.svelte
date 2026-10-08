<script lang="ts">
  // The answer key region under the page: derived from the document's questions, in
  // order, with the same numbering as the body. Read-only; free-form entries (W2) will
  // add editable slots here.
  import { fmtAnswer } from '../format'
  import type { Question } from '../types'

  export let questions: Question[] = []
</script>

<section class="key" aria-label="Answer key">
  <h2>Answer key</h2>
  {#if questions.length === 0}
    <p class="empty">Answers appear here as you add questions.</p>
  {/if}
  <ol>
    {#each questions as q, i (i)}
      {@const part = q.question.parts[0]}
      <li class="entry">
        <div class="head">
          <span class="n">{i + 1}.</span>
          <span class="ans"><span class="label">Answer</span> {fmtAnswer(part.answer)}</span>
          <span class="marks">[{part.marks}]</span>
        </div>
        {#if part.solution_steps?.length}
          <ol class="steps">
            {#each part.solution_steps as s, j (j)}<li>{s.text}</li>{/each}
          </ol>
        {/if}
        {#if part.marking_scheme?.length}
          <ul class="scheme">
            {#each part.marking_scheme as m, j (j)}
              <li><span class="mtag {m.type}">{m.type}{m.mark}</span> {m.description}</li>
            {/each}
          </ul>
        {/if}
      </li>
    {/each}
  </ol>
</section>

<style>
  .key {
    width: 210mm;
    max-width: 100%;
    margin: 1.5rem auto 0;
    background: var(--paper-2);
    border: 1px dashed var(--line);
    border-radius: 8px;
    padding: 1rem 1.4rem;
    box-sizing: border-box;
  }
  h2 {
    margin: 0 0 0.6rem;
    font-family: var(--serif);
    font-size: 1.2rem;
  }
  .empty {
    color: var(--ink-faint);
    margin: 0;
  }
  ol,
  ul {
    margin: 0;
    padding: 0;
    list-style: none;
  }
  .entry {
    margin: 0 0 0.9rem;
  }
  .head {
    display: flex;
    gap: 0.6rem;
    align-items: baseline;
  }
  .n {
    font-family: var(--mono);
    font-weight: 600;
    color: var(--ink-soft);
  }
  .label {
    font-family: var(--mono);
    font-size: 11px;
    color: var(--verify-ink);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .ans {
    font-family: var(--serif);
    font-weight: 600;
  }
  .marks {
    margin-left: auto;
    font-family: var(--mono);
    color: var(--mark);
  }
  .steps {
    list-style: decimal;
    padding-left: 2rem;
    color: var(--ink-soft);
    font-size: 13.5px;
    margin-top: 0.2rem;
  }
  .scheme {
    padding-left: 2rem;
    font-size: 12.5px;
    color: var(--ink-faint);
  }
  .mtag {
    font-family: var(--mono);
    font-weight: 600;
    margin-right: 0.3rem;
  }
</style>
