<script lang="ts">
  // The answer key region under the page: one entry per numbered question, in document
  // order, with the same numbering as the body. Templated entries are generated and
  // read-only; a free-form entry shows its question and an editable answer (written back to
  // the question's node by the page).
  import { createEventDispatcher } from 'svelte'
  import { fmtAnswer } from '../format'
  import type { Question } from '../types'
  import { blocksToHtml, type DocJSON, type DocNode } from './doc'
  import AnswerEditor from './AnswerEditor.svelte'
  import { typesetMath } from './math'
  import FragmentView from './FragmentView.svelte'

  export let blocks: DocNode[] = []

  const dispatch = createEventDispatcher<{
    answer: { blockId: string; answer: DocJSON }
    error: string
  }>()
</script>

<section class="key" aria-label="Answer key">
  <h2>Answer key</h2>
  {#if blocks.length === 0}
    <p class="empty">Answers appear here as you add questions.</p>
  {/if}
  <ol>
    {#each blocks as block, i (block.attrs?.block_id ?? i)}
      {#if block.type === 'freeformQuestion'}
        {@const marks = block.attrs?.marks as number | null | undefined}
        <li class="entry freeform" data-block-id={block.attrs?.block_id}>
          <div class="head">
            <span class="n">{i + 1}.</span>
            <span class="label">Answer</span>
            {#if marks !== null && marks !== undefined}<span class="marks">[{marks}]</span>{/if}
          </div>
          <div class="qtext" use:typesetMath={blocksToHtml(block.content)}>
            <!-- eslint-disable-next-line svelte/no-at-html-tags -- escaped by blocksToHtml -->
            {@html blocksToHtml(block.content)}
          </div>
          <AnswerEditor
            value={(block.attrs?.answer as DocJSON) ?? { type: 'doc', content: [] }}
            label={`Answer to question ${i + 1}`}
            on:error={(e) => dispatch('error', e.detail)}
            on:change={(e) =>
              dispatch('answer', { blockId: String(block.attrs?.block_id), answer: e.detail.answer })}
          />
        </li>
      {:else}
      {@const q = block.attrs?.question as Question}
      {@const part = q.question.parts[0]}
      {#if q.source_type === 'sourced'}
        <!-- bank question: the engine's own key markup, so MCQ options, tables and
             constructions are right; it carries its own number. -->
        <li class="entry"><FragmentView question={q} mode="key" number={i + 1} /></li>
      {:else}
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
      {/if}
      {/if}
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
  .qtext {
    font-family: var(--serif);
    color: var(--ink-soft);
    margin: 0.2rem 0 0.4rem 1.6rem;
  }
  .qtext :global(img) {
    max-width: 100%;
    height: auto;
  }
  .qtext :global(p) {
    margin: 0.15rem 0;
  }
  .freeform :global(.answer) {
    margin-left: 1.6rem;
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
