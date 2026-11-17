<script lang="ts">
  // O3: the "+ New" dialog. Four choices as option cards (new folder, exam set, single paper,
  // blank paper), then a step or two each. (A separate Template choice made the same papers as
  // Single paper → Start it empty, so it was dropped.) A single paper opens in the editor; an exam
  // set makes its three papers one after the other into one folder (each told the topics of those
  // already made, Paper 2 first, EXA-153, so the set spreads its topics), says which failed (and keeps
  // what was made), then shows the folder. Escape goes back a step, or closes on the first;
  // focus stays in the dialog, and the list puts it back on the button that opened it.
  import { onMount, tick } from 'svelte'
  import {
    createDocument,
    createFolder,
    generatePaper,
    type Folder,
    type PaperReport,
    type PaperTemplateInfo,
  } from './docsApi'
  import type { DocumentRecord, DocumentSummary } from './doc'
  import { PARTS, PART_TEMPLATES, SET_FILL_ORDER, type PaperPart } from './folders'
  import { lastReport } from './paperReport'
  import { navigate } from '../router'

  export let folders: Folder[]
  export let templates: PaperTemplateInfo[]
  export let levels: string[]
  /** The folder whose "+ New in folder" opened the wizard: the default home for what it makes. */
  export let contextFolder: Folder | null = null
  export let onClose: () => void
  export let onFolderCreated: (f: Folder) => void
  export let onPapersCreated: (docs: DocumentSummary[]) => void
  /** Close the wizard and bring the folder into view (after an exam set). */
  export let onShowFolder: (id: string) => void

  type Step = 'choose' | 'folder' | 'set-folder' | 'set-content' | 'set-progress' | 'single' | 'single-how'
  type Choice = 'folder' | 'set' | 'single' | 'blank'

  const CHOICES: { key: Choice; title: string; desc: string }[] = [
    { key: 'folder', title: 'New folder', desc: 'An empty folder to keep papers together.' },
    { key: 'set', title: 'Exam set', desc: 'Paper 1 Booklet A, Booklet B and Paper 2 in one folder.' },
    { key: 'single', title: 'Single paper', desc: 'One Booklet A, Booklet B or Paper 2: generated, or empty with its cover and sections.' },
    { key: 'blank', title: 'Blank paper', desc: 'An empty paper to write from scratch.' },
  ]
  const TITLES: Record<Step, string> = {
    choose: 'New',
    folder: 'New folder',
    'set-folder': 'Exam set',
    'set-content': 'Exam set',
    'set-progress': 'Exam set',
    single: 'Single paper',
    'single-how': 'Single paper',
  }

  let step: Step = 'choose'
  let trail: Step[] = []
  let dialog: HTMLDivElement
  let busy = false
  let error = ''
  let announce = ''

  // New folder
  let folderName = ''
  // Exam set: 'new' or an existing folder's id; the new folder's name; what to make.
  let setWhere: string = contextFolder?.id ?? 'new'
  let setName = 'P6 exam set'
  let setFolderId: string | null = null
  let setLevel: string | null = null
  type Row = {
    part: PaperPart
    label: string
    state: 'waiting' | 'working' | 'done' | 'failed'
    error?: string
    /** A generated paper's questions per topic (its report), for the set's later papers. */
    topics?: Record<string, number>
  }
  let rows: Row[] = []
  // Single paper
  let singleCode = ''
  let singleFolder: string = contextFolder?.id ?? ''

  const msg = (e: unknown): string => (e instanceof Error ? e.message : String(e))
  const summaryOf = (r: DocumentRecord): DocumentSummary => ({
    id: r.id,
    title: r.title,
    total_marks: r.total_marks,
    version: r.version,
    created_at: r.created_at,
    updated_at: r.updated_at,
    folder_id: r.folder_id ?? null,
    paper_part: r.paper_part ?? null,
  })
  $: partTemplates = PARTS.map((p) => templates.find((t) => t.code === PART_TEMPLATES[p.key])).filter(
    (t): t is PaperTemplateInfo => !!t,
  )
  $: singleLabel = templates.find((t) => t.code === singleCode)?.label ?? ''
  $: running = rows.some((r) => r.state === 'working' || r.state === 'waiting')
  $: failed = rows.filter((r) => r.state === 'failed')
  $: made = rows.filter((r) => r.state === 'done')
  $: whereName = setWhere === 'new' ? setName.trim() : (folders.find((f) => f.id === setWhere)?.name ?? setName.trim())

  async function focusStep() {
    await tick()
    const target = dialog?.querySelector<HTMLElement>('[data-autofocus]') ?? focusables()[0]
    target?.focus()
  }
  onMount(focusStep)

  async function go(next: Step) {
    error = ''
    trail = [...trail, step]
    step = next
    await focusStep()
  }

  async function back() {
    if (busy || trail.length === 0) return
    error = ''
    step = trail[trail.length - 1]
    trail = trail.slice(0, -1)
    await focusStep()
  }

  function close() {
    if (busy || running) return
    onClose()
  }

  function focusables(): HTMLElement[] {
    if (!dialog) return []
    return [
      ...dialog.querySelectorAll<HTMLElement>(
        'button:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
      ),
    ].filter((el) => !(el instanceof HTMLInputElement && el.type === 'radio' && !el.checked))
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      e.preventDefault()
      e.stopPropagation()
      if (step !== 'choose' && step !== 'set-progress') void back()
      else close()
      return
    }
    if (e.key !== 'Tab') return onOptionKeys(e)
    // Keep focus in the dialog: wrap at either end.
    const all = focusables()
    if (all.length === 0) return
    const first = all[0]
    const last = all[all.length - 1]
    const active = document.activeElement
    if (e.shiftKey && (active === first || !dialog.contains(active))) {
      e.preventDefault()
      last.focus()
    } else if (!e.shiftKey && (active === last || !dialog.contains(active))) {
      e.preventDefault()
      first.focus()
    }
  }

  /** Arrow keys (and Home/End) move between the option cards or chips of one group. */
  function onOptionKeys(e: KeyboardEvent) {
    const keys = ['ArrowDown', 'ArrowRight', 'ArrowUp', 'ArrowLeft', 'Home', 'End']
    if (!keys.includes(e.key)) return
    const group = (e.target as HTMLElement).closest?.('[data-options]')
    if (!group) return
    const opts = [...group.querySelectorAll<HTMLButtonElement>('button[data-opt]:not([disabled])')]
    if (opts.length === 0) return
    e.preventDefault()
    const i = opts.indexOf(document.activeElement as HTMLButtonElement)
    const n = opts.length
    const j =
      e.key === 'Home' ? 0
      : e.key === 'End' ? n - 1
      : e.key === 'ArrowDown' || e.key === 'ArrowRight' ? (i + 1) % n
      : (i - 1 + n) % n
    opts[j].focus()
  }

  async function choose(c: Choice) {
    if (c === 'folder') return go('folder')
    if (c === 'set') return go('set-folder')
    if (c === 'single') return go('single')
    await openNew(() => createDocument(undefined, undefined, contextFolder?.id ?? null))
  }

  /** Make one paper, then open it in the editor. */
  async function openNew(make: () => Promise<DocumentRecord & { report?: PaperReport }>) {
    if (busy) return
    busy = true
    error = ''
    try {
      const rec = await make()
      if (rec.report) lastReport.set({ docId: rec.id, report: rec.report })
      navigate(`/docs/${rec.id}`)
      busy = false
      onClose()
    } catch (e) {
      error = msg(e)
      busy = false
    }
  }

  async function onCreateFolder() {
    const name = folderName.trim()
    if (!name || busy) return
    busy = true
    error = ''
    try {
      const f = await createFolder(name)
      onFolderCreated(f)
      busy = false
      onShowFolder(f.id)
    } catch (e) {
      error = msg(e)
      busy = false
    }
  }

  async function makeSet(level: string | null) {
    if (busy) return
    error = ''
    setLevel = level
    busy = true
    try {
      if (setWhere === 'new') {
        const f = await createFolder(setName.trim())
        onFolderCreated(f)
        setWhere = f.id
      }
      setFolderId = setWhere
    } catch (e) {
      error = `The folder could not be made, so no paper was: ${msg(e)}`
      busy = false
      return
    }
    busy = false
    rows = PARTS.map((p) => ({ part: p.key, label: p.label, state: 'waiting' }))
    trail = []
    step = 'set-progress'
    await runRows()
  }

  /** Make the waiting papers one at a time (each is a full generation), keeping each result. A
   *  generated set is filled Paper 2 first (EXA-153); the rows keep their printed order. A paper
   *  that fails doesn't stop the rest: they are made without its topics, and a retried paper is
   *  told the topics of every paper made by then. So a retried Paper 2 still spreads its topics
   *  over the set, but chooses last, and may take more easier-rung questions than usual. */
  async function runRows() {
    const folderId = setFolderId
    const order = setLevel ? SET_FILL_ORDER.flatMap((k) => rows.filter((r) => r.part === k)) : rows
    for (const row of order) {
      if (row.state !== 'waiting') continue
      row.state = 'working'
      rows = rows
      const code = PART_TEMPLATES[row.part]
      try {
        let rec: DocumentRecord
        if (setLevel) {
          const made = await generatePaper(code, setLevel, folderId, setTopicsSoFar())
          row.topics = made.report?.topics
          rec = made
        } else rec = await createDocument(undefined, code, folderId)
        row.state = 'done'
        onPapersCreated([summaryOf(rec)])
        announce = `${row.label} made.`
      } catch (e) {
        row.state = 'failed'
        row.error = msg(e)
        announce = `${row.label} could not be made.`
      }
      rows = rows
    }
    if (!rows.some((r) => r.state === 'failed') && folderId) onShowFolder(folderId)
    else await focusStep()
  }

  /** EXA-153: questions per topic in the set's papers made so far, so each new paper spreads its
   *  topics over the whole set rather than repeating them in every paper. */
  function setTopicsSoFar(): Record<string, number> {
    const out: Record<string, number> = {}
    for (const r of rows) for (const [t, n] of Object.entries(r.topics ?? {})) out[t] = (out[t] ?? 0) + n
    return out
  }

  async function retryFailed() {
    rows = rows.map((r) => (r.state === 'failed' ? { ...r, state: 'waiting', error: undefined } : r))
    await runRows()
  }

  function pickSingle(code: string) {
    singleCode = code
    void go('single-how')
  }

  const plural = (n: number, w: string) => `${n} ${w}${n === 1 ? '' : 's'}`
  const listParts = (rs: Row[]) => rs.map((r) => r.label).join(' and ')
  function describe(t: PaperTemplateInfo): string {
    const marks = t.sections.reduce((s, x) => s + x.marks_target, 0)
    const qs = t.sections.reduce((s, x) => s + x.questions, 0)
    const time = t.time_min >= 60 ? `${Math.floor(t.time_min / 60)} h${t.time_min % 60 ? ` ${t.time_min % 60} min` : ''}` : `${t.time_min} min`
    return `${plural(t.sections.length, 'section')} · ${plural(qs, 'question')} · ${marks} marks · ${time}`
  }
</script>

<div class="backdrop" role="presentation" on:click|self={close}>
  <div
    class="dialog"
    role="dialog"
    aria-modal="true"
    aria-labelledby="nw-title"
    tabindex="-1"
    bind:this={dialog}
    on:keydown={onKeydown}
  >
    <header>
      {#if trail.length > 0 && step !== 'set-progress'}
        <button class="icon" aria-label="Back" disabled={busy} on:click={back}>
          <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M20 11H7.8l5.6-5.6L12 4l-8 8 8 8 1.4-1.4L7.8 13H20z" /></svg>
        </button>
      {/if}
      <h2 id="nw-title">{TITLES[step]}</h2>
      <button class="icon close" aria-label="Close" disabled={busy || running} on:click={close}>
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M19 6.4 17.6 5 12 10.6 6.4 5 5 6.4 10.6 12 5 17.6 6.4 19 12 13.4 17.6 19 19 17.6 13.4 12z" /></svg>
      </button>
    </header>

    {#if step === 'choose'}
      {#if contextFolder}<p class="lead">Papers go in <b>{contextFolder.name}</b>.</p>{/if}
      <div class="cards" role="group" aria-label="What to make" data-options>
        {#each CHOICES as c, i (c.key)}
          <button
            class="card"
            data-opt
            data-autofocus={i === 0 ? '' : undefined}
            aria-labelledby={`nw-l-${c.key}`}
            aria-describedby={`nw-d-${c.key}`}
            disabled={busy}
            on:click={() => choose(c.key)}
          >
            <span class="cicon" aria-hidden="true">
              {#if c.key === 'folder'}
                <svg viewBox="0 0 24 24"><path d="M3 6.5A1.5 1.5 0 0 1 4.5 5h4.6l2 2h8.4A1.5 1.5 0 0 1 21 8.5v9a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 17.5z" /></svg>
              {:else if c.key === 'set'}
                <svg viewBox="0 0 24 24"><path d="M8 2h10a2 2 0 0 1 2 2v12h-2V4H8zM4 6h10a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z" /></svg>
              {:else if c.key === 'single'}
                <svg viewBox="0 0 24 24"><path d="M6 2h8l6 6v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zm7 1.5V9h5.5zM7 12v2h10v-2zm0 4v2h7v-2z" /></svg>
              {:else}
                <svg viewBox="0 0 24 24"><path d="M6 2h8l6 6v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zm7 1.5V9h5.5z" /></svg>
              {/if}
            </span>
            <span class="ctext">
              <span class="ctitle" id={`nw-l-${c.key}`}>{c.title}</span>
              <span class="cdesc" id={`nw-d-${c.key}`}>{c.desc}</span>
            </span>
          </button>
        {/each}
      </div>
    {:else if step === 'folder'}
      <form class="stack" aria-label="New folder" on:submit|preventDefault={onCreateFolder}>
        <label class="field">
          <span>Folder name</span>
          <input data-autofocus bind:value={folderName} placeholder="e.g. 2026 Prelims" maxlength="80" required />
        </label>
        <div class="actions">
          <button class="btn primary" type="submit" disabled={busy || !folderName.trim()}>Create folder</button>
        </div>
      </form>
    {:else if step === 'set-folder'}
      <form class="stack" aria-label="Exam set folder" on:submit|preventDefault={() => go('set-content')}>
        <p class="lead">
          One each of <b>Paper 1 Booklet A</b>, <b>Booklet B</b> and <b>Paper 2</b>, filed together.
        </p>
        <fieldset>
          <legend>Put them in</legend>
          <div class="chips">
            <label class="chip" class:on={setWhere === 'new'}>
              <input type="radio" name="nw-where" value="new" bind:group={setWhere} data-autofocus={setWhere === 'new' ? '' : undefined} />
              {#if setWhere === 'new'}<svg class="check" viewBox="0 0 24 24" aria-hidden="true"><path d="M9.5 16.2 5.3 12l-1.4 1.4 5.6 5.6 11-11-1.4-1.4z" /></svg>{/if}
              A new folder
            </label>
            {#each folders as f (f.id)}
              <label class="chip" class:on={setWhere === f.id}>
                <input type="radio" name="nw-where" value={f.id} bind:group={setWhere} data-autofocus={setWhere === f.id ? '' : undefined} />
                {#if setWhere === f.id}<svg class="check" viewBox="0 0 24 24" aria-hidden="true"><path d="M9.5 16.2 5.3 12l-1.4 1.4 5.6 5.6 11-11-1.4-1.4z" /></svg>{/if}
                {f.name}
              </label>
            {/each}
          </div>
        </fieldset>
        {#if setWhere === 'new'}
          <label class="field">
            <span>Folder name</span>
            <input bind:value={setName} maxlength="80" required />
          </label>
        {/if}
        <div class="actions">
          <button class="btn primary" type="submit" disabled={setWhere === 'new' && !setName.trim()}>Next</button>
        </div>
      </form>
    {:else if step === 'set-content'}
      <p class="lead">
        Into {setWhere === 'new' ? 'the new folder' : 'the folder'} <b>{whereName}</b>.
        Generated papers fill every question the content allows and leave placeholders for the rest;
        empty starters have the cover and sections only.
      </p>
      <div class="cards" role="group" aria-label="How to make the papers" data-options>
        {#each levels as l, i (l)}
          <button class="card compact" data-opt data-autofocus={i === levels.length - 1 ? '' : undefined} disabled={busy} on:click={() => makeSet(l)}>
            <span class="ctitle">Generate at {l}</span>
          </button>
        {/each}
        <button class="card compact" data-opt disabled={busy} on:click={() => makeSet(null)}>
          <span class="ctitle">Empty starters</span>
        </button>
      </div>
    {:else if step === 'set-progress'}
      <p class="lead">
        {setLevel ? `Generating at ${setLevel}` : 'Empty starters'} into <b>{whereName}</b>.
      </p>
      <ol class="progress" aria-label="Exam set papers">
        {#each rows as r (r.part)}
          <li class={r.state} data-part={r.part}>
            <span class="pstate" aria-hidden="true">
              {#if r.state === 'done'}
                <svg viewBox="0 0 24 24"><path d="M9.5 16.2 5.3 12l-1.4 1.4 5.6 5.6 11-11-1.4-1.4z" /></svg>
              {:else if r.state === 'failed'}
                <svg viewBox="0 0 24 24"><path d="M11 7h2v7h-2zm0 9h2v2h-2zM12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z" /></svg>
              {:else if r.state === 'working'}
                <span class="spin"></span>
              {/if}
            </span>
            <span class="plabel">{r.label}</span>
            <span class="pnote">
              {r.state === 'done' ? 'Made' : r.state === 'failed' ? 'Failed' : r.state === 'working' ? 'Making…' : 'Waiting'}
            </span>
          </li>
        {/each}
      </ol>
      {#if !running && failed.length > 0}
        <div class="failure" role="alert">
          <p>
            <b>{listParts(failed)}</b> could not be made.
            {#if made.length > 0}{listParts(made)} {made.length === 1 ? 'is' : 'are'} in <b>{whereName}</b>.{/if}
          </p>
          <ul>
            {#each failed as r (r.part)}<li>{r.label}: {r.error}</li>{/each}
          </ul>
        </div>
        <div class="actions">
          <button class="btn" data-autofocus on:click={retryFailed}>Try {failed.length === 1 ? failed[0].label : 'them'} again</button>
          {#if setFolderId}
            <button class="btn primary" on:click={() => setFolderId && onShowFolder(setFolderId)}>Show the folder</button>
          {/if}
        </div>
      {/if}
    {:else if step === 'single'}
      <div class="cards" role="group" aria-label="Which paper" data-options>
        {#each partTemplates as t, i (t.code)}
          <button class="card" data-opt data-autofocus={i === 0 ? '' : undefined} aria-labelledby={`nw-sl-${t.code}`} aria-describedby={`nw-s-${t.code}`} on:click={() => pickSingle(t.code)}>
            <span class="ctext">
              <span class="ctitle" id={`nw-sl-${t.code}`}>{t.label}</span>
              <span class="cdesc" id={`nw-s-${t.code}`}>{describe(t)}</span>
            </span>
          </button>
        {/each}
      </div>
    {:else if step === 'single-how'}
      <p class="lead"><b>{singleLabel}</b></p>
      <label class="field">
        <span>Folder (optional)</span>
        <select bind:value={singleFolder}>
          <option value="">No folder</option>
          {#each folders as f (f.id)}<option value={f.id}>{f.name}</option>{/each}
        </select>
      </label>
      <div class="cards" role="group" aria-label="How to make it" data-options>
        {#each levels as l, i (l)}
          <button
            class="card compact"
            data-opt
            data-autofocus={i === levels.length - 1 ? '' : undefined}
            disabled={busy}
            on:click={() => openNew(() => generatePaper(singleCode, l, singleFolder || null))}
          >
            <span class="ctitle">Generate at {l}</span>
          </button>
        {/each}
        <button class="card compact" data-opt disabled={busy} on:click={() => openNew(() => createDocument(undefined, singleCode, singleFolder || null))}>
          <span class="ctitle">Start it empty</span>
        </button>
      </div>
    {/if}

    {#if busy && step !== 'set-progress'}<p class="working">Working…</p>{/if}
    {#if error}<p class="error" role="alert">{error}</p>{/if}
    <p class="sr" role="status">{announce}</p>
  </div>
</div>

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba(25, 28, 33, 0.45);
    display: grid;
    place-items: center;
    z-index: 50;
    padding: 16px;
  }
  .dialog {
    background: var(--page);
    border: 1px solid var(--line);
    border-radius: 16px; /* M3 corner-large for dialogs is 28px; 16 keeps our calmer cards */
    box-shadow: var(--shadow);
    width: min(520px, 100%);
    max-height: calc(100vh - 32px);
    overflow: auto;
    padding: 0.75rem 1rem 1.1rem;
    box-sizing: border-box;
  }
  .dialog:focus {
    outline: none;
  }
  header {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    min-height: 40px;
    margin-bottom: 0.5rem;
  }
  h2 {
    margin: 0;
    font-family: var(--serif);
    font-size: 1.25rem;
    font-weight: 600;
  }
  .icon {
    position: relative;
    display: inline-grid;
    place-items: center;
    width: 40px;
    height: 40px;
    border: none;
    border-radius: 20px;
    background: none;
    color: var(--ink-soft);
    cursor: pointer;
    overflow: hidden;
  }
  .icon svg {
    fill: currentColor;
  }
  .close {
    margin-left: auto;
  }
  .lead {
    margin: 0 0 0.75rem;
    font-size: 14px;
    color: var(--ink-soft);
  }
  .lead b {
    color: var(--ink);
  }

  /* Option cards: M3 outlined cards that act like large assist chips (12px corners, a
     one-pixel outline, a leading icon, and the M3 state layer on hover / focus / press). */
  .cards {
    display: grid;
    gap: 0.5rem;
  }
  .card {
    position: relative;
    display: flex;
    align-items: center;
    gap: 0.8rem;
    width: 100%;
    min-height: 56px;
    box-sizing: border-box;
    padding: 0.65rem 0.9rem;
    border: 1px solid var(--line);
    border-radius: 12px;
    background: var(--page);
    color: var(--ink);
    font: inherit;
    text-align: left;
    cursor: pointer;
    overflow: hidden;
  }
  .card.compact {
    min-height: 44px;
  }
  .cicon {
    flex: none;
    display: inline-grid;
    place-items: center;
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: var(--verify-soft);
  }
  .cicon svg {
    width: 20px;
    height: 20px;
    fill: var(--verify-ink);
  }
  .ctext {
    display: grid;
    gap: 2px;
    min-width: 0;
  }
  .ctitle {
    font-size: 15px;
    font-weight: 600;
  }
  .cdesc {
    font-size: 13px;
    color: var(--ink-faint);
  }

  /* State layers (M3): the content colour over the surface at 8% hover, 12% focus / press. */
  .card::before,
  .icon::before,
  .chip::before,
  .btn::before {
    content: '';
    position: absolute;
    inset: 0;
    background: currentColor;
    opacity: 0;
    pointer-events: none;
    transition: opacity 120ms;
  }
  .card:hover::before,
  .icon:hover::before,
  .chip:hover::before,
  .btn:hover::before {
    opacity: 0.08;
  }
  .card:focus-visible::before,
  .card:active::before,
  .icon:focus-visible::before,
  .icon:active::before,
  .chip:focus-within::before,
  .btn:focus-visible::before,
  .btn:active::before {
    opacity: 0.12;
  }
  .card:focus-visible,
  .icon:focus-visible,
  .btn:focus-visible,
  .chip:has(input:focus-visible),
  .field input:focus-visible,
  .field select:focus-visible {
    outline: 2px solid var(--verify);
    outline-offset: 2px;
  }
  .card:disabled,
  .icon:disabled,
  .btn:disabled {
    opacity: 0.55;
    cursor: default;
  }
  .card:disabled::before,
  .btn:disabled::before {
    opacity: 0;
  }

  .stack {
    display: grid;
    gap: 0.75rem;
  }
  fieldset {
    border: none;
    margin: 0;
    padding: 0;
  }
  legend,
  .field span {
    font-size: 13px;
    font-weight: 600;
    color: var(--ink-soft);
    margin-bottom: 0.35rem;
    padding: 0;
  }
  .field {
    display: grid;
    gap: 0.35rem;
    margin-bottom: 0.75rem;
  }
  .stack .field {
    margin-bottom: 0;
  }
  .field input,
  .field select {
    font: inherit;
    font-size: 14px;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--page);
    color: var(--ink);
    padding: 0.5rem 0.6rem;
    min-height: 40px;
    box-sizing: border-box;
  }

  /* M3 filter chips (single choice): 32px, 8px corners, outline when off, verify-soft and a
     leading check when on. Native radios underneath give arrow keys and the radio semantics. */
  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }
  .chip {
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    height: 32px;
    box-sizing: border-box;
    padding: 0 0.85rem;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--page);
    color: var(--ink-soft);
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    overflow: hidden;
    max-width: 100%;
  }
  .chip.on {
    border-color: transparent;
    background: var(--verify-soft);
    color: var(--verify-ink);
    padding-left: 0.5rem;
  }
  .chip input {
    position: absolute;
    opacity: 0;
    width: 1px;
    height: 1px;
    margin: 0;
  }
  .check {
    width: 18px;
    height: 18px;
    fill: currentColor;
  }

  .actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 0.5rem;
    margin-top: 0.75rem;
  }
  .stack .actions {
    margin-top: 0;
  }
  .btn {
    position: relative;
    font: inherit;
    font-size: 14px;
    font-weight: 600;
    min-height: 40px;
    padding: 0 1.1rem;
    border: 1px solid var(--line);
    border-radius: 20px;
    background: var(--page);
    color: var(--verify-ink);
    cursor: pointer;
    overflow: hidden;
  }
  .btn.primary {
    border-color: var(--verify);
    background: var(--verify);
    color: #fff;
  }

  .progress {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 0.4rem;
  }
  .progress li {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 0.55rem 0.8rem;
    font-size: 14px;
  }
  .progress li.done {
    background: var(--verify-soft);
    border-color: transparent;
  }
  .progress li.failed {
    background: var(--mark-soft);
    border-color: var(--mark);
  }
  .pstate {
    display: inline-grid;
    place-items: center;
    width: 20px;
    height: 20px;
  }
  .pstate svg {
    width: 20px;
    height: 20px;
  }
  .done .pstate svg {
    fill: var(--verify-ink);
  }
  .failed .pstate svg {
    fill: var(--mark);
  }
  .plabel {
    font-weight: 600;
  }
  .pnote {
    margin-left: auto;
    font-size: 13px;
    color: var(--ink-faint);
  }
  .spin {
    width: 14px;
    height: 14px;
    border: 2px solid var(--line);
    border-top-color: var(--verify);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .spin {
      animation: none;
    }
    .card::before,
    .icon::before,
    .chip::before,
    .btn::before {
      transition: none;
    }
  }
  .failure {
    margin-top: 0.75rem;
    border: 1px solid var(--mark);
    background: var(--mark-soft);
    border-radius: 12px;
    padding: 0.6rem 0.8rem;
    font-size: 14px;
  }
  .failure p {
    margin: 0;
  }
  .failure ul {
    margin: 0.35rem 0 0;
    padding-left: 1.1rem;
    font-size: 13px;
    color: var(--ink-soft);
    overflow-wrap: anywhere;
  }
  .working {
    margin: 0.75rem 0 0;
    font-size: 13px;
    color: var(--ink-faint);
  }
  .error {
    margin: 0.75rem 0 0;
    color: var(--mark);
    font-size: 14px;
    overflow-wrap: anywhere;
  }
  .sr {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
  }
</style>
