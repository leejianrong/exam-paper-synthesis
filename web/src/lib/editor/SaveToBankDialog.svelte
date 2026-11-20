<script lang="ts">
  // "Save to your bank…" on a teacher's own question (EXA-90): file it under a topic and level,
  // then keep a copy in the owner's question bank to insert into other papers. A copy already
  // there (saved from this block before) is reported, and replaced only when asked.
  import Dialog from '../Dialog.svelte'
  import { listBankTopics, saveOwnQuestion, type BankTopic } from '../api'
  import { errorText } from '../errors'
  import { cleanNode, type DocNode } from './doc'

  type Level = 'P5' | 'P6'
  type Difficulty = 'easy' | 'medium' | 'hard'

  let {
    block,
    level: paperLevel = '',
    onSaved,
    onClose,
  }: {
    block: DocNode
    /** The paper's level, when it has one: the question's level starts there. */
    level?: string
    onSaved: (result: { status: 'saved' | 'replaced'; id: string }) => void
    onClose: () => void
  } = $props()

  const parts = $derived((block.content ?? []).filter((c) => c.type === 'freeformPart'))
  const partMarks = $derived(parts.reduce((n, p) => n + (Number(p.attrs?.marks) || 0), 0))

  let topics = $state<BankTopic[]>([])
  let topic = $state('')
  // svelte-ignore state_referenced_locally
  let level = $state<Level>(paperLevel === 'P5' ? 'P5' : 'P6')
  let difficulty = $state<Difficulty>('medium')
  // svelte-ignore state_referenced_locally
  let marks = $state<number | null>(typeof block.attrs?.marks === 'number' ? block.attrs.marks : null)
  let busy = $state(false)
  let error = $state('')
  let duplicate = $state(false)

  $effect(() => {
    listBankTopics()
      .then((t) => (topics = t))
      .catch((e) => (error = errorText(e, "Couldn't load the topics")))
  })

  const ready = $derived(!!topic && (parts.length > 0 || (marks !== null && marks >= 0)))

  async function save(replace = false) {
    if (!ready || busy) return
    busy = true
    error = ''
    try {
      const result = await saveOwnQuestion({
        block: cleanNode(block) as unknown as Record<string, unknown>,
        topic,
        level,
        difficulty,
        marks: parts.length ? null : marks,
        replace,
      })
      if (result.status === 'duplicate') duplicate = true
      else onSaved({ status: result.status, id: result.id ?? '' })
    } catch (e) {
      error = errorText(e, "Couldn't save the question to your bank")
    } finally {
      busy = false
    }
  }

  const close = () => {
    if (!busy) onClose()
  }
</script>

<Dialog title="Save to your bank" width="26rem" onClose={close}>
  <form
    onsubmit={(e) => {
      e.preventDefault()
      void save(duplicate)
    }}
  >
    <p class="hint">Keep a copy of this question to use in other papers. It stays your own question: the app does not check its answer.</p>
    <label>
      Topic
      <select bind:value={topic} required disabled={duplicate}>
        <option value="" disabled>Choose a topic</option>
        {#each topics as t (t.topic)}<option value={t.topic}>{t.topic}</option>{/each}
      </select>
    </label>
    <div class="pair">
      <label>
        Level
        <select bind:value={level} disabled={duplicate}>
          <option value="P5">P5</option>
          <option value="P6">P6</option>
        </select>
      </label>
      <label>
        Difficulty
        <select bind:value={difficulty} disabled={duplicate}>
          <option value="easy">Easy</option>
          <option value="medium">Medium</option>
          <option value="hard">Hard</option>
        </select>
      </label>
      {#if parts.length}
        <p class="marks">{partMarks} mark{partMarks === 1 ? '' : 's'}<span>set on each part</span></p>
      {:else}
        <label>
          Marks
          <input type="number" min="0" max="100" bind:value={marks} required disabled={duplicate} />
        </label>
      {/if}
    </div>
    {#if duplicate}
      <p class="dup" role="alert">This question is already in your bank. Replace the copy there with this one?</p>
    {/if}
    {#if error}<p class="error" role="alert">{error}</p>{/if}
    <div class="row">
      <button class="primary" type="submit" disabled={busy || !ready}>{duplicate ? 'Replace it' : 'Save'}</button>
      <button type="button" disabled={busy} onclick={close}>Cancel</button>
    </div>
  </form>
</Dialog>

<style>
  form {
    display: flex;
    flex-direction: column;
    gap: var(--s3);
  }
  label {
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 12.5px;
    font-weight: 600;
    color: var(--ink-soft);
  }
  select,
  input {
    font: inherit;
    font-size: 13px;
    height: 32px;
    padding: 0 var(--s2);
    border: 1px solid var(--line);
    border-radius: var(--r-sm);
    background: var(--page);
    color: var(--ink);
  }
  input {
    width: 5rem;
  }
  .pair {
    display: flex;
    gap: var(--s3);
    align-items: flex-end;
  }
  .marks {
    margin: 0;
    font-size: 13px;
    font-weight: 600;
    display: flex;
    flex-direction: column;
    line-height: 1.3;
  }
  .marks span {
    font-weight: 400;
    font-size: 12px;
    color: var(--ink-soft);
  }
  .row {
    display: flex;
    gap: var(--s2);
  }
  button {
    font: inherit;
    font-size: 13px;
    font-weight: 600;
    height: 32px;
    padding: 0 var(--s3);
    border: 1px solid var(--line);
    border-radius: var(--r-sm);
    background: var(--page);
    color: var(--ink);
    cursor: pointer;
  }
  button:hover:not(:disabled) {
    background: var(--wash);
  }
  .primary {
    background: var(--verify);
    border-color: var(--verify);
    color: var(--on-accent);
  }
  .primary:hover:not(:disabled) {
    background: var(--verify-ink);
  }
  button:disabled {
    opacity: 0.5;
    cursor: default;
  }
  .hint {
    margin: 0;
    color: var(--ink-soft);
  }
  .dup {
    margin: 0;
    color: var(--ink);
  }
  .error {
    margin: 0;
    color: var(--mark);
    font-size: 12.5px;
  }
</style>
