<script lang="ts">
  // The chrome around a templated question inside the page: the question body, and (EXA-161)
  // its controls, which show only when the block is selected: a pill with "Another like this",
  // Lock and a ⋯ menu of everything else (QuestionBar). Every edit replaces the block's frozen
  // snapshot with the child object the API returns (lineage intact).
  import { errorText } from '../errors'
  import type { Readable } from 'svelte/store'
  import { editQuestion, setCosmetic, setNumbers, type EditOp } from '../api'
  import type { Question } from '../types'
  import { confirmAction } from '../confirm'
  import NamesPopover from './NamesPopover.svelte'
  import NumbersPopover from './NumbersPopover.svelte'
  import FragmentView from './FragmentView.svelte'
  import QuestionBody from './QuestionBody.svelte'
  import AnswerArea from './AnswerArea.svelte'
  import QuestionBar from './QuestionBar.svelte'
  import LockBadge from './LockBadge.svelte'
  import type { BlockLayout } from './layout'
  import type { SectionPlacement } from './doc'
  import type { SwapMode } from './docsApi'
  import type { PaperSlot } from './templatedQuestion'
  import type { BlockPlace } from './blockPlace'
  import { blockLabel, type QuestionAction, type QuestionFacts } from './questionMenu'

  export let store: Readable<Question>
  export let layout: Readable<BlockLayout>
  export let paperSlot: Readable<PaperSlot>
  /** Where this question's [n] print: its section's effective placement (EXA-152). */
  export let placement: Readable<SectionPlacement>
  export let place: Readable<BlockPlace>
  /** The node view's element (the focusable group the controls belong to). */
  export let host: HTMLElement
  export let ctx: {
    /** An edit's reply; `from` is the question the edit started from (dropped if it changed). */
    replace: (q: Question, from: string) => void
    remove: () => void
    move: (dir: -1 | 1) => void
    addBelow: () => void
    convert: () => Promise<void>
    setLayout: (patch: Partial<BlockLayout>) => void
    swap: (mode: SwapMode) => Promise<void>
    setLocked: (locked: boolean) => void
    setInKey: (inKey: boolean) => void
  }

  $: q = $store
  $: part = q.question.parts[0]
  $: multipart = q.question.parts.length > 1
  // A multiple-choice copy (P8b) can't be rebuilt with new names: the engine refuses it.
  $: isChoice = q.question.parts.some((p) => p.answer?.type === 'choice')
  // Only written answers get working space and an Ans: line (not MCQ, not a construction).
  $: writtenParts = q.question.parts.filter(
    (p) => !['choice', 'construction'].includes(p.answer?.type ?? ''),
  )
  // A sourced (bank) question is teacher-vouched: drawn by the engine's print renderer, with
  // none of the engine-only edits. Its status lives in the inspector, not on the page.
  $: fromBank = q.source_type === 'sourced'
  // A generated multi-part question (P8c) is drawn the same way, so its stem and every
  // lettered part show; it keeps its engine edits (the API offers only whole-question ones).
  $: engineDrawn = fromBank || multipart
  $: ops = (q.available_ops ?? []) as EditOp[]
  // P8d: a question the paper generator put here can be swapped for another, or locked.
  $: generated = $paperSlot.generated
  $: locked = $paperSlot.locked
  $: barView =
    part.diagram?.type === 'bar_model_before_after' ? (part.diagram.view_mode ?? 'grouped') : null
  $: totalMarks = q.question.parts.reduce((n, p) => n + (p.marks ?? 0), 0) || null

  $: facts = {
    kind: generated ? 'generated' : 'bank',
    locked,
    lockable: generated,
    inKey: $paperSlot.inKey,
    ops,
    canEditNames: q.source_type !== 'sourced' && !!q.blueprint_code && !isChoice,
    canAddPart: false,
    canMoveUp: $place.canMoveUp,
    canMoveDown: $place.canMoveDown,
    opLabels: {
      // toggle-diagram is only offered for bar models, which print in the answer key only (EXA-132)
      'toggle-diagram': part.diagram ? 'Hide model from key' : 'Show model in key',
      'toggle-bar-view': barView === 'sliced' ? 'Group segments' : 'Slice into units',
    },
  } satisfies QuestionFacts
  $: host.setAttribute('aria-label', blockLabel($place.number, totalMarks, facts))

  let busy = false
  let error = ''
  let editingNames = false
  let editingNumbers = false

  async function run(fn: () => Promise<Question | void>) {
    busy = true
    error = ''
    const from = q.id
    try {
      const next = await fn()
      if (next) ctx.replace(next, from)
      // a closing form would drop focus to the page: give it back to the block
      if (editingNames || editingNumbers) host.focus()
      editingNames = false
      editingNumbers = false
    } catch (e) {
      error = errorText(e, "The question wasn't changed")
    } finally {
      busy = false
    }
  }

  async function convert() {
    const ok = await confirmAction({
      title: 'Edit as your own text?',
      body: "You can then change any of it, but it won't be checked by the engine any more.",
      confirmLabel: 'Edit as my own text',
    })
    if (ok) await run(() => ctx.convert())
  }

  function act(action: QuestionAction) {
    switch (action) {
      case 'like':
      case 'topic':
      case 'own':
        return run(() => ctx.swap(action))
      case 'regenerate':
        return run(() => editQuestion('regenerate', q))
      case 'easier':
        return run(() => editQuestion('make-easier', q))
      case 'harder':
        return run(() => editQuestion('make-harder', q))
      case 'names':
        editingNames = !editingNames
        return
      case 'numbers':
        editingNumbers = !editingNumbers
        error = ''
        return
      case 'lock':
        return ctx.setLocked(!locked)
      case 'key':
        return ctx.setInKey(!$paperSlot.inKey)
      case 'up':
        return ctx.move(-1)
      case 'down':
        return ctx.move(1)
      case 'addBelow':
        return ctx.addBelow()
      case 'convert':
        return convert()
      case 'delete':
        return ctx.remove()
      default:
        if (action.startsWith('op:')) return run(() => editQuestion(action.slice(3) as EditOp, q))
    }
  }
</script>

<div class="block" data-testid="question-block">
  <div class="num">
    {#if locked}<LockBadge />{/if}
  </div>
  <div class="main">
    {#if engineDrawn}
      <FragmentView question={q} paper={{ placement: $placement, answerArea: false }} />
    {:else}
      <QuestionBody {q} placement={$placement} />
    {/if}

    {#each writtenParts as p, i (i)}
      <AnswerArea
        marks={p.marks ?? null}
        label={multipart ? (p.label ?? '') : ''}
        placement={$placement}
        spaceMm={$layout.space_mm}
        unit={$layout.ans_unit ?? p.answer?.unit ?? null}
        onSpace={(mm) => ctx.setLayout({ space_mm: mm })}
        onUnit={(u) => ctx.setLayout({ ans_unit: u })}
      />
    {/each}

    {#if editingNames}
      <NamesPopover
        {q}
        {busy}
        on:apply={(e) => run(() => setCosmetic(q, e.detail.changes))}
        on:close={() => (editingNames = false)}
      />
    {/if}

    {#if editingNumbers}
      <NumbersPopover
        {q}
        {busy}
        {error}
        on:apply={(e) => run(() => setNumbers(q, e.detail.changes))}
        on:close={() => {
          editingNumbers = false
          error = ''
        }}
      />
    {/if}

    {#if error && !editingNumbers}
      <p class="error" role="alert">{error}</p>
    {/if}
  </div>
  <QuestionBar {host} {facts} number={$place.number} selected={$place.selected} {busy} onAction={act} />
</div>

<style>
  .block {
    display: grid;
    grid-template-columns: 2rem 1fr;
    gap: 0.25rem;
  }
  .num {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  .num::before {
    content: counter(q) '.';
    font-family: var(--mono);
    font-weight: 600;
    color: var(--ink-soft);
  }
  .error {
    color: var(--mark);
    font-size: 12.5px;
    margin: 0.3rem 0 0;
  }
</style>
