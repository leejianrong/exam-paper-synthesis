<script lang="ts">
  // "Edit answer…" (EXA-162): the written answer to one of the teacher's own questions, or to
  // each of its parts, with the question above it for reference. Each change goes straight onto
  // the question's node (one undoable step, autosaved), so the key view redraws behind it.
  import Dialog from '../Dialog.svelte'
  import AnswerEditor from './AnswerEditor.svelte'
  import { blocksToHtml, freeformParts, type DocJSON, type DocNode } from './doc'
  import { partLetter } from './freeformPart'
  import { typesetMath } from './math'

  let {
    number,
    block,
    onAnswer,
    onPartAnswer,
    onError,
    onClose,
  }: {
    number: number
    block: DocNode
    onAnswer: (answer: DocJSON) => void
    onPartAnswer: (index: number, answer: DocJSON) => void
    onError: (message: string) => void
    onClose: () => void
  } = $props()

  const parts = $derived(freeformParts(block))
  const stem = $derived((block.content ?? []).filter((c) => c.type !== 'freeformPart'))
  const answerOf = (n: DocNode) => (n.attrs?.answer as DocJSON | undefined) ?? { type: 'doc', content: [] }
</script>

<Dialog title="Answer to question {number}" width="40rem" {onClose}>
  <div class="qtext" use:typesetMath={blocksToHtml(stem)}>
    <!-- eslint-disable-next-line svelte/no-at-html-tags -- escaped by blocksToHtml -->
    {@html blocksToHtml(stem)}
  </div>
  {#if parts.length}
    {#each parts as part, i (i)}
      <div class="part">
        <div class="qtext" use:typesetMath={blocksToHtml(part.content)}>
          <span class="plabel">({partLetter(i)})</span>
          <!-- eslint-disable-next-line svelte/no-at-html-tags -- escaped by blocksToHtml -->
          {@html blocksToHtml(part.content)}
        </div>
        <AnswerEditor
          value={answerOf(part)}
          label="Answer to question {number} part ({partLetter(i)})"
          autofocus={i === 0}
          on:error={(e) => onError(e.detail)}
          on:change={(e) => onPartAnswer(i, e.detail.answer)}
        />
      </div>
    {/each}
  {:else}
    <AnswerEditor
      value={answerOf(block)}
      label="Answer to question {number}"
      autofocus
      on:error={(e) => onError(e.detail)}
      on:change={(e) => onAnswer(e.detail.answer)}
    />
  {/if}
  <p class="note">One line prints after Ans: in the school key. Write more lines for working, and they print as you write them.</p>
  <div class="actions">
    <button class="done" type="button" onclick={onClose}>Done</button>
  </div>
</Dialog>

<style>
  .qtext {
    margin: 0 0 var(--s2);
    color: var(--ink-soft);
    font-family: var(--serif);
  }
  .qtext :global(p) {
    margin: 0.15rem 0;
  }
  .qtext :global(img) {
    max-width: 100%;
    height: auto;
  }
  .plabel {
    float: left;
    margin-right: 6px;
    font-weight: 600;
    color: var(--ink);
  }
  .part {
    margin-top: var(--s3);
  }
  .note {
    margin: var(--s3) 0 0;
    font-size: 12.5px;
    color: var(--ink-faint);
  }
  .actions {
    display: flex;
    justify-content: flex-end;
    margin-top: var(--s3);
  }
  .done {
    height: 32px;
    padding: 0 var(--s4);
    border: 1px solid var(--verify);
    border-radius: var(--r-sm);
    background: var(--verify);
    color: var(--on-accent);
    font: inherit;
    font-weight: 600;
    cursor: pointer;
  }
  .done:hover {
    background: var(--verify-ink);
  }
</style>
