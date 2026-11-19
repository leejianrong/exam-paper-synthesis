<script lang="ts">
  import { BlockSelectionGuard, insertBlockSafely } from './blockSelection'
  import Icon from '../Icon.svelte'
  import Menu, { type MenuItem } from '../Menu.svelte'
  import ConfirmDialog from '../ConfirmDialog.svelte'
  import EditorBar from './EditorBar.svelte'
  import SidePanel, { type SectionRow } from './SidePanel.svelte'
  import { describePage, summarisePages, type PageSummary } from './pageSummary'
  import { paperSettings } from './paperSettings'
  import {
    DEFAULT_PLACEMENT,
    keyOptionsOf,
    numberFrom,
    type KeyLayout,
    type KeyToggle,
    type MarksPlacement,
  } from './layout'
  // The WYSIWYG page (W1c): an A4-width column of rich text and question blocks, a "+"
  // to add questions, the answer key below, autosave, and the export/preview menu.
  import { onDestroy, onMount } from 'svelte'
  import { Editor } from '@tiptap/core'
  import StarterKit from '@tiptap/starter-kit'
  import { NodeSelection, TextSelection } from '@tiptap/pm/state'
  import type { Question } from '../types'
  import AddQuestion from './AddQuestion.svelte'
  import AnswerKey from './AnswerKey.svelte'
  import { withReviewed } from './inspector'
  import { createAutosaver, type Autosaver } from './autosave'
  import {
    buildDocument,
    freeformNode,
    numberedNodes,
    paperOutline,
    totalMarks,
    type DocJSON,
    type DocumentRecord,
  } from './doc'
  import {
    ApiError,
    exportDocument,
    getDocument,
    listFolders,
    previewDocument,
    regeneratePaper,
    saveDocument,
    swapQuestion,
    unfilledDetail,
    type ExportMode,
    type SwapMode,
  } from './docsApi'
  import { FreeformQuestion, QuestionDocument, insertFreeform } from './freeformQuestion'
  import { IMAGE_TYPES, uploadAsset } from './assets'
  import MathPopover from './MathPopover.svelte'
  import { openMathEditor } from './mathEditor'
  import { ImageBlock, ImageUpload, MathNode, uploadAndInsert } from './media'
  import { PageBreak } from './pageBreak'
  import { BlankPage, CoverPage, blankPageNode, coverNode } from './pages'
  import { lastReport, reportSummary, unfilledPlaceholders } from './paperReport'
  import {
    applyServerContent,
    goToQuestion,
    hasGeneratedSlots,
    regenerateCounts,
    regenerateNotice,
    swapNotice,
  } from './paperOps'
  import PrintWarning from './PrintWarning.svelte'
  import { Section, outline } from './sections'
  import { loadQuota, type Quota } from '../session'
  import { TemplatedQuestion, questionNode } from './templatedQuestion'
  import { BlockShortcuts } from './shortcuts'

  export let id: string

  let element: HTMLDivElement
  let editor: Editor | null = null
  let autosaver: Autosaver | null = null
  let unsubscribe: (() => void) | null = null

  let title = ''
  let loadError = ''
  let loading = true
  let content: DocJSON = { type: 'doc', content: [] }
  let status: 'saved' | 'dirty' | 'saving' | 'conflict' | 'error' = 'saved'
  let pickerAt: number | null | undefined = undefined // undefined = closed, null = end
  let busy = ''
  let actionError = ''
  let notice = ''
  /** EXA-161: a question was just deleted; the toast offers the editor's undo. */
  let deleted = false
  let deletedTimer: ReturnType<typeof setTimeout> | undefined
  /** EXA-137: the export refused a paper with empty placeholders; ask before printing it. */
  let unfilled: { mode: ExportMode; questions: number[] } | null = null
  let quota: Quota | null = null
  let selectedId: string | null = null // the block the author is in (for the inspector)
  let previewHtml: string | null = null
  let readToken = 0
  let pageSummary: PageSummary | null = null // the paginated preview's pages and tallies (P6d)
  let barH = 0 // the sticky top bar's height: the formatting toolbar sticks just below it
  let tick = 0 // bumps on every editor transaction so toolbar state re-reads
  let folderName: string | null = null
  let titleInput: HTMLInputElement
  let panelTab: 'paper' | 'question' = 'paper'
  let confirmRegen = false
  let innerWidth = 1440
  /** Below 1024 px the toolbar's tail (lists, equation, image) moves into its ⋯ menu. */
  $: narrow = innerWidth < 1024

  $: blocks = numberedNodes(content)
  $: marks = totalMarks(content)
  $: coverPresent = content.content?.[0]?.type === 'coverPage'
  $: placeholdersLeft = unfilledPlaceholders(content)
  $: canRegenerate = hasGeneratedSlots(content)
  // The generator's report (P8a), shown once on the paper it made.
  $: generated = $lastReport && $lastReport.docId === id ? reportSummary($lastReport.report) : ''
  $: start = numberFrom($paperSettings)
  $: outline.set(paperOutline(content, start))
  $: keyOpts = keyOptionsOf($paperSettings)
  $: regenInfo = canRegenerate ? regenerateCounts(content) : null

  // The side panel's Marks group and the header total: each section against its target.
  $: sectionRows = sectionRowsOf(content, start)
  $: target =
    sectionRows.length && sectionRows.every((r) => r.target !== null)
      ? sectionRows.reduce((sum, r) => sum + (r.target ?? 0), 0)
      : null
  $: offTarget = sectionRows
    .filter((r) => r.target !== null && r.marks !== r.target)
    .map((r, i) => `${r.title || `Section ${i + 1}`}: ${r.marks} of ${r.target} marks`)
    .join('; ')

  function sectionRowsOf(doc: DocJSON, first: number): SectionRow[] {
    const titles = (doc.content ?? [])
      .filter((n) => n.type === 'section')
      .map((n) => String(n.attrs?.title ?? '').trim())
    return paperOutline(doc, first).map((o, i) => ({ title: titles[i] || `Section ${i + 1}`, marks: o.marks, target: o.target }))
  }

  const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`
  $: regenBody = regenInfo
    ? `Replaces ${plural(regenInfo.unlocked, 'unlocked question')}. ` +
      (regenInfo.locked
        ? `${plural(regenInfo.locked, 'locked question')} ${regenInfo.locked === 1 ? 'stays' : 'stay'}. `
        : 'No questions are locked. ') +
      'Questions you wrote yourself stay.'
    : ''

  function rename() {
    titleInput?.focus()
    titleInput?.select()
  }

  function setPlacement(e: Event) {
    const marks_placement = (e.target as HTMLSelectElement).value as MarksPlacement
    paperSettings.update((s) => ({ ...s, marks_placement }))
    scheduleSave()
  }

  function setKeyOption(name: KeyToggle, value: boolean) {
    paperSettings.update((s) => ({ ...s, key_options: { ...s.key_options, [name]: value } }))
    scheduleSave()
  }

  function setKeyLayout(e: Event) {
    const layout = (e.currentTarget as HTMLSelectElement).value as KeyLayout
    paperSettings.update((s) => ({ ...s, key_options: { ...s.key_options, layout } }))
    scheduleSave()
  }

  const setInKey = (blockId: string, included: boolean) =>
    setBlockAttrs(blockId, ['templatedQuestion', 'freeformQuestion'], { in_key: included })

  function setTime(e: Event) {
    const raw = (e.target as HTMLInputElement).value
    const n = raw === '' ? null : Math.max(1, Math.min(600, Math.round(+raw)))
    paperSettings.update((s) => ({ ...s, time_min: n }))
    scheduleSave()
  }

  // EXA-134: Booklet B carries on from Booklet A, so its first question is 16, not 1.
  function setNumberFrom(e: Event) {
    const raw = (e.target as HTMLInputElement).value
    const n = raw === '' ? null : Math.max(1, Math.min(999, Math.round(+raw)))
    paperSettings.update((s) => ({ ...s, number_from: n }))
    scheduleSave()
  }

  // P8d: while the server swaps or regenerates, nothing is saved (a save would race the op,
  // or put the pre-op document back afterwards); a change made meanwhile is remembered and
  // saved on top of the server's version once it is in.
  let opInFlight = false
  let editedDuringOp = false
  let applyingServer = false // the server already saved what is being applied

  function scheduleSave() {
    if (!editor || !autosaver || applyingServer) return
    if (opInFlight) {
      editedDuringOp = true
      return
    }
    autosaver.schedule(buildDocument(title, editor.getJSON() as DocJSON, $paperSettings))
  }

  onMount(async () => {
    void loadQuota().then((q) => (quota = q))
    try {
      const rec = await getDocument(id)
      title = rec.document.title
      paperSettings.set({
        marks_placement: DEFAULT_PLACEMENT,
        ...(rec.document.settings ?? {}),
      })
      content = rec.document.content
      if (rec.folder_id) {
        const folder = rec.folder_id
        void listFolders()
          .then((fs) => (folderName = fs.find((f) => f.id === folder)?.name ?? null))
          .catch(() => undefined)
      }
      autosaver = createAutosaver({
        initialVersion: rec.version,
        save: (doc, base) => saveDocument(id, doc, base),
      })
      unsubscribe = autosaver.status.subscribe((s) => (status = s))

      editor = new Editor({
        element,
        extensions: [
          StarterKit.configure({
            document: false,
            heading: { levels: [1, 2, 3] },
            // Only the node/mark types the document schema allows (document.schema.json).
            blockquote: false,
            code: false,
            codeBlock: false,
            horizontalRule: false,
            strike: false,
            link: false,
          }),
          QuestionDocument,
          ImageBlock,
          MathNode,
          ImageUpload.configure({
            upload: (f: File) => uploadAsset(f, f.name),
            onError: (m: string) => (actionError = m),
          }),
          PageBreak,
          Section,
          CoverPage,
          BlankPage,
          BlockSelectionGuard,
          BlockShortcuts,
          FreeformQuestion.configure({
            onAddBelow: (pos: number) => (pickerAt = pos),
            onSwap: swapBlock,
            onDeleted: questionDeleted,
          }),
          TemplatedQuestion.configure({
            onAddBelow: (pos: number) => (pickerAt = pos),
            onNotice: (m: string) => (notice = m),
            onSwap: swapBlock,
            onDeleted: questionDeleted,
          }),
        ],
        content: rec.document.content,
        onUpdate: ({ editor: e }) => {
          content = e.getJSON() as DocJSON
          scheduleSave()
        },
        onTransaction: () => (tick += 1),
      })
      startWithTextCursor(editor)
      content = editor.getJSON() as DocJSON
      tick += 1 // the toolbar reads the opening selection, before any transaction
    } catch (e) {
      loadError =
        e instanceof ApiError && e.status === 404
          ? 'This paper was not found.'
          : e instanceof Error
            ? e.message
            : String(e)
    } finally {
      loading = false
    }
  })

  onDestroy(() => {
    clearTimeout(deletedTimer)
    void autosaver?.flush()
    unsubscribe?.()
    editor?.destroy()
  })

  function onBeforeUnload(e: BeforeUnloadEvent) {
    if (status === 'dirty' || status === 'saving' || status === 'error') e.preventDefault()
  }

  /** A paper that opens on an atom block (cover page, section) starts with that whole block
   *  selected; the first click into the still-unfocused editor kept that selection, so the
   *  first keys typed replaced the block. Open with a text cursor instead (the last place text
   *  can go). */
  function startWithTextCursor(ed: Editor) {
    const { state } = ed
    if (!(state.selection instanceof NodeSelection)) return
    const sel = TextSelection.findFrom(state.doc.resolve(state.doc.content.size), -1, true)
    if (sel) ed.view.dispatch(state.tr.setSelection(sel))
  }

  function questionDeleted() {
    deleted = true
    clearTimeout(deletedTimer)
    deletedTimer = setTimeout(() => (deleted = false), 8000)
  }

  function undoDelete() {
    deleted = false
    clearTimeout(deletedTimer)
    editor?.chain().focus().undo().run()
  }

  function trackBlock(e: Event) {
    const host = (e.target as HTMLElement).closest('[data-block-id]')
    selectedId = host?.getAttribute('data-block-id') ?? null
  }

  function insertionPoint(editor: Editor): number {
    const { doc } = editor.state
    // "Add question" at the end goes before the editor's empty trailing paragraph, so
    // repeated inserts stack with no blank gap between them.
    const last = doc.lastChild
    const trailing = last?.type.name === 'paragraph' && last.content.size === 0
    return pickerAt ?? (trailing && last ? doc.content.size - last.nodeSize : doc.content.size)
  }

  function insertQuestion(q: Question) {
    if (!editor) return
    editor.chain().insertContentAt(insertionPoint(editor), questionNode(q)).scrollIntoView().run()
    editor.view.focus() // now, not a frame later (TipTap's focus() defers; keys would be lost)
    pickerAt = undefined
  }

  function insertFreeformQuestion() {
    if (!editor) return
    insertFreeform(editor, insertionPoint(editor), freeformNode())
    pickerAt = undefined
  }

  // Set attributes on the question block with this id (both kinds), as one undoable step.
  function setBlockAttrs(blockId: string, kinds: string[], attrs: Record<string, unknown>) {
    if (!editor) return
    const { doc, tr } = editor.state
    let target: number | null = null
    doc.descendants((node, pos) => {
      if (target === null && kinds.includes(node.type.name) && node.attrs.block_id === blockId)
        target = pos
      return false
    })
    if (target === null) return
    const node = doc.nodeAt(target)
    if (!node) return
    tr.setNodeMarkup(target, undefined, { ...node.attrs, ...attrs })
    editor.view.dispatch(tr)
  }

  // A free-form answer is edited in the key region and stored on its question's node.
  const setAnswer = (blockId: string, answer: DocJSON) =>
    setBlockAttrs(blockId, ['freeformQuestion'], { answer })

  // A part's written answer: the nth freeformPart inside the question with this id.
  function setPartAnswer(blockId: string, index: number, answer: DocJSON) {
    if (!editor) return
    const { doc, tr } = editor.state
    let target: number | null = null
    doc.descendants((node, pos) => {
      if (node.type.name !== 'freeformQuestion' || node.attrs.block_id !== blockId) return true
      let n = 0
      node.forEach((child, offset) => {
        if (child.type.name !== 'freeformPart') return
        if (n++ === index) target = pos + 1 + offset
      })
      return false
    })
    if (target === null) return
    const node = doc.nodeAt(target)
    if (!node) return
    tr.setNodeMarkup(target, undefined, { ...node.attrs, answer })
    editor.view.dispatch(tr)
  }

  // Review (ADR-0019) is stored on the paper's own copy of a bank question as well as in the bank.
  function setReviewed(blockId: string, reviewed: boolean) {
    const node = blocks.find((b) => b.attrs?.block_id === blockId)
    if (!node || node.type !== 'templatedQuestion') return
    setBlockAttrs(blockId, ['templatedQuestion'], {
      question: withReviewed(node.attrs?.question as Question, reviewed),
    })
  }

  // A remark is the author's private note, edited in the inspector; it never prints.
  const setRemark = (blockId: string, remark: string) =>
    setBlockAttrs(blockId, ['templatedQuestion', 'freeformQuestion'], { remark: remark || null })

  let fileInput: HTMLInputElement

  async function onPickImages() {
    const files = Array.from(fileInput.files ?? [])
    fileInput.value = ''
    if (!editor) return
    actionError = ''
    await uploadAndInsert(editor, files, {
      upload: (f) => uploadAsset(f, f.name),
      onError: (m) => (actionError = m),
    })
  }

  function addEquation() {
    const e = editor
    if (!e) return
    openMathEditor({
      latex: '',
      apply: (latex) => {
        if (latex) e.chain().focus().insertContent({ type: 'math', attrs: { latex } }).run()
      },
    })
  }

  // Toolbar state, re-read after every editor transaction (`tick`).
  function readActive(revision: number) {
    const e = editor
    return {
      revision,
      inText: e?.state.selection.$from.parent.isTextblock ?? false,
      bold: e?.isActive('bold') ?? false,
      italic: e?.isActive('italic') ?? false,
      underline: e?.isActive('underline') ?? false,
      bullet: e?.isActive('bulletList') ?? false,
      ordered: e?.isActive('orderedList') ?? false,
      h1: e?.isActive('heading', { level: 1 }) ?? false,
      h2: e?.isActive('heading', { level: 2 }) ?? false,
      h3: e?.isActive('heading', { level: 3 }) ?? false,
    }
  }
  $: act = readActive(tick)
  $: styleName = act.h1 ? 'Heading 1' : act.h2 ? 'Heading 2' : act.h3 ? 'Heading 3' : 'Normal text'
  const EQUATION_OFF = 'Equation: click into a line of text first, then insert it there'

  /** Run an editor command from a menu and put the caret back in the paper at once. */
  function inPaper(run: (e: Editor) => void) {
    const e = editor
    if (!e) return
    run(e)
    e.view.focus()
  }

  const styleItems: MenuItem[] = [
    { label: 'Normal text', onSelect: () => inPaper((e) => e.chain().setParagraph().run()) },
    ...([1, 2, 3] as const).map((level) => ({
      label: `Heading ${level}`,
      onSelect: () => inPaper((e) => e.chain().setHeading({ level }).run()),
    })),
  ]

  // The toolbar's ⋯: page-level inserts for now (S5 moves them to the Insert menu), plus the
  // toolbar's tail when the window is narrow.
  $: moreItems = [
    ...(narrow
      ? ([
          { label: 'Bulleted list', icon: 'bullets', onSelect: () => inPaper((e) => e.chain().toggleBulletList().run()) },
          { label: 'Numbered list', icon: 'numbers', onSelect: () => inPaper((e) => e.chain().toggleOrderedList().run()) },
          {
            label: 'Equation',
            icon: 'sigma',
            disabled: !act.inText,
            hint: act.inText ? undefined : EQUATION_OFF,
            onSelect: addEquation,
          },
          { label: 'Image', icon: 'image', onSelect: () => fileInput.click() },
        ] satisfies MenuItem[])
      : []),
    {
      label: 'Cover page',
      icon: 'cover',
      separator: narrow,
      disabled: coverPresent,
      hint: coverPresent ? 'The paper already has a cover page' : 'Add a cover page at the start',
      onSelect: () => inPaper((e) => e.chain().insertContentAt(0, coverNode()).run()),
    },
    {
      label: 'Blank page',
      icon: 'blankpage',
      hint: 'Insert a blank or rough-work page',
      onSelect: () => inPaper((e) => insertBlockSafely(e, blankPageNode())),
    },
    {
      label: 'Page break',
      icon: 'pagebreak',
      onSelect: () => inPaper((e) => insertBlockSafely(e, { type: 'pageBreak' })),
    },
  ] satisfies MenuItem[]

  async function download(mode: ExportMode, allowPlaceholders = false) {
    busy = `export-${mode}`
    actionError = ''
    unfilled = null
    try {
      await autosaver?.flush()
      const blob = await exportDocument(id, mode, allowPlaceholders)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${title || 'paper'}-${mode}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      const empty = unfilledDetail(e)
      if (empty) unfilled = { mode, questions: empty.questions }
      else actionError = e instanceof Error ? e.message : String(e)
    } finally {
      busy = ''
      void loadQuota().then((q) => (quota = q))
    }
  }

  function fillPlaceholders() {
    const first = unfilled?.questions[0]
    unfilled = null
    if (editor && first !== undefined) goToQuestion(editor, first, start)
  }

  /** P8d: a server-side change to the saved paper (swap, regenerate). Pending edits are saved
   *  first and the server works on exactly that version. The page is inert meanwhile; if
   *  anything changes anyway it isn't saved until the op is done, then it is saved on top of
   *  the server's version. The editor takes only the blocks the server changed (compared with
   *  the paper as it was sent), one undoable step. */
  async function paperOp<R>(
    run: (baseVersion: number) => Promise<DocumentRecord & { report: R }>,
    describe: (report: R) => string,
  ) {
    const ed = editor
    if (!ed || !autosaver || busy) return
    busy = 'paper'
    actionError = ''
    opInFlight = true
    editedDuringOp = false
    ed.setEditable(false, false)
    // What the server will work on: every change up to now is saved by the flush below, and
    // nothing after this point is (opInFlight).
    const sent = ed.getJSON() as DocJSON
    try {
      await autosaver.flush()
      if (status === 'conflict') return
      if (status === 'error') throw new Error('Your latest changes are not saved yet. Try again in a moment.')
      const rec = await run(autosaver.version())
      applyingServer = true
      try {
        applyServerContent(ed, sent, rec.document.content)
      } finally {
        applyingServer = false
      }
      autosaver.rebase(rec.version)
      content = ed.getJSON() as DocJSON
      notice = describe(rec.report)
    } catch (e) {
      actionError =
        e instanceof ApiError && e.status === 409
          ? 'This paper changed in another tab or window. Reload to get the latest version.'
          : e instanceof ApiError && typeof e.detail === 'string'
            ? e.detail
            : e instanceof Error
              ? e.message
              : String(e)
    } finally {
      opInFlight = false
      ed.setEditable(true, false)
      busy = ''
      if (editedDuringOp) scheduleSave()
    }
  }

  function swapBlock(blockId: string, mode: SwapMode): Promise<void> {
    return paperOp((base) => swapQuestion(id, blockId, mode, base), swapNotice)
  }

  function regenerate(): Promise<void> {
    return paperOp((base) => regeneratePaper(id, base), regenerateNotice)
  }

  // The preview paginates itself after it loads (fonts, maths); read what it decided once it has.
  function readPages(e: Event) {
    const frame = e.currentTarget as HTMLIFrameElement
    const mine = ++readToken // a newer load (or a closed preview) cancels this poll
    pageSummary = null
    let tries = 0
    const look = () => {
      const d = frame.contentDocument
      if (mine !== readToken || !d || previewHtml === null) return
      if (d.documentElement.getAttribute('data-paginated') === 'true') {
        const s = summarisePages(d, start)
        pageSummary = s.paginated ? s : null
      } else if (tries++ < 200) setTimeout(look, 150) // heavy papers can take a while
    }
    look()
  }

  async function preview(mode: ExportMode) {
    busy = 'preview'
    actionError = ''
    pageSummary = null
    readToken++
    try {
      await autosaver?.flush()
      previewHtml = await previewDocument(id, mode)
    } catch (e) {
      actionError = e instanceof Error ? e.message : String(e)
    } finally {
      busy = ''
    }
  }
</script>

<svelte:window on:beforeunload={onBeforeUnload} bind:innerWidth />

<header class="ehead" bind:clientHeight={barH} inert={busy === 'paper'}>
  <EditorBar
    {title}
    {folderName}
    {status}
    {marks}
    {target}
    {offTarget}
    {busy}
    {quota}
    hasQuestions={blocks.length > 0}
    onPreview={() => preview('full')}
    onExport={(mode) => download(mode)}
    onRename={rename}
  />
  <!-- Clicking a tool must not take focus from the page (like Word/Docs): the editor keeps its
       caret, so keys typed right after a click go to the paper, not the button (a space would
       "press" it again; TipTap's focus() only refocuses a frame later). Keyboard use is unaffected. -->
  <div
    class="tools"
    role="toolbar"
    aria-label="Formatting"
    tabindex="-1"
    on:mousedown|preventDefault>
    <button class="btn quiet" title="Add a question" on:click={() => (pickerAt = null)}
      ><Icon name="plus" />Question</button
    >
    <button
      class="btn quiet"
      title="Insert a section"
      on:click={() => editor && insertBlockSafely(editor, { type: 'section', attrs: { title: '' } })}
      ><Icon name="plus" />Section</button
    >
    <span class="sep"></span>
    <button
      class="icon-btn"
      aria-label="Undo"
      title="Undo (Ctrl+Z)"
      on:click={() => editor?.chain().focus().undo().run()}><Icon name="undo" /></button
    >
    <button
      class="icon-btn"
      aria-label="Redo"
      title="Redo (Ctrl+Y)"
      on:click={() => editor?.chain().focus().redo().run()}><Icon name="redo" /></button
    >
    <span class="sep"></span>
    <Menu items={styleItems} label="Text style: {styleName}" menuLabel="Text style" triggerClass="styleselect">
      {#snippet trigger()}<span class="style-name">{styleName}</span><Icon name="down" />{/snippet}
    </Menu>
    <span class="sep"></span>
    <button
      class="icon-btn"
      aria-label="Bold"
      title="Bold (Ctrl+B)"
      aria-pressed={act.bold}
      on:click={() => editor?.chain().focus().toggleBold().run()}><b>B</b></button
    >
    <button
      class="icon-btn"
      aria-label="Italic"
      title="Italic (Ctrl+I)"
      aria-pressed={act.italic}
      on:click={() => editor?.chain().focus().toggleItalic().run()}><i>I</i></button
    >
    <button
      class="icon-btn"
      aria-label="Underline"
      title="Underline (Ctrl+U)"
      aria-pressed={act.underline}
      on:click={() => editor?.chain().focus().toggleUnderline().run()}><u>U</u></button
    >
    {#if !narrow}
      <span class="sep"></span>
      <button
        class="icon-btn"
        aria-pressed={act.bullet}
        aria-label="Bulleted list"
        title="Bulleted list"
        on:click={() => editor?.chain().focus().toggleBulletList().run()}><Icon name="bullets" /></button
      >
      <button
        class="icon-btn"
        aria-pressed={act.ordered}
        aria-label="Numbered list"
        title="Numbered list"
        on:click={() => editor?.chain().focus().toggleOrderedList().run()}><Icon name="numbers" /></button
      >
      <span class="sep"></span>
      <button
        class="icon-btn"
        aria-label="Equation"
        title={act.inText ? 'Equation' : EQUATION_OFF}
        aria-disabled={!act.inText}
        on:click={() => act.inText && addEquation()}><Icon name="sigma" /></button
      >
      <button class="icon-btn" aria-label="Image" title="Insert image" on:click={() => fileInput.click()}
        ><Icon name="image" /></button
      >
    {/if}
    <input
      bind:this={fileInput}
      type="file"
      accept={IMAGE_TYPES.join(',')}
      multiple
      hidden
      aria-label="Choose image"
      on:change={onPickImages}
    />
    <span class="tail">
      <Menu items={moreItems} label="More tools" align="end" triggerClass="icon-btn" triggerTitle="More tools">
        {#snippet trigger()}<Icon name="more" />{/snippet}
      </Menu>
    </span>
  </div>
</header>

{#if status === 'conflict'}
  <p class="banner" role="alert">
    This paper changed in another tab or window. Your latest edits were not saved.
    <button on:click={() => location.reload()}>Reload</button>
  </p>
{/if}
{#if actionError}<p class="banner err" role="alert">{actionError}</p>{/if}
{#if generated}
  <p class="banner note" aria-live="polite" data-testid="generate-report">
    {generated} <button on:click={() => lastReport.set(null)}>Dismiss</button>
  </p>
{/if}
{#if notice}
  <p class="banner note" aria-live="polite">
    {notice} <button on:click={() => (notice = '')}>Dismiss</button>
  </p>
{/if}

{#if deleted}
  <div class="toast" role="status">
    Question deleted · <button on:click={undoDelete}>Undo</button>
  </div>
{/if}

{#if loading}
  <p class="loading">Loading…</p>
{:else if loadError}
  <p class="banner err" role="alert">{loadError} <a href="#/">Back to papers</a></p>
{/if}

<div
  class="desk"
  class:hidden={loading || !!loadError}
  style="--bar-h:{barH}px"
  inert={busy === 'paper'}
  aria-busy={busy === 'paper'}
>
<div class="main">
  <div class="page">
    <input
      class="title"
      aria-label="Paper title"
      placeholder="Untitled paper"
      bind:this={titleInput}
      bind:value={title}
      on:input={scheduleSave}
    />
    <p class="sheetmeta"><span>Name: ______________</span><span>Total: {marks} marks</span></p>
    <div
      class="surface"
      style:--q-start={start - 1}
      role="presentation"
      bind:this={element}
      on:click={trackBlock}
      on:focusin={trackBlock}
      on:keyup={trackBlock}
    ></div>

    <button class="plus" aria-label="Add question" on:click={() => (pickerAt = null)}>
      <span class="plus-sign">+</span> Add question
    </button>
  </div>

  <AnswerKey
    {blocks}
    {start}
    options={keyOpts}
    on:include={(e) => setInKey(e.detail.blockId, e.detail.included)}
    on:answer={(e) => setAnswer(e.detail.blockId, e.detail.answer)}
    on:partanswer={(e) => setPartAnswer(e.detail.blockId, e.detail.index, e.detail.answer)}
    on:error={(e) => (actionError = e.detail)}
  />
</div>
<SidePanel
  bind:tab={panelTab}
  {blocks}
  {marks}
  {selectedId}
  {start}
  sections={sectionRows}
  regen={regenInfo}
  {placeholdersLeft}
  busy={!!busy}
  on:time={(e) => setTime(e.detail)}
  on:numberfrom={(e) => setNumberFrom(e.detail)}
  on:placement={(e) => setPlacement(e.detail)}
  on:regenerate={() => (confirmRegen = true)}
  on:remark={(e) => setRemark(e.detail.blockId, e.detail.remark)}
  on:review={(e) => setReviewed(e.detail.blockId, e.detail.reviewed)}
>
  <!-- EXA-160: a temporary home for the key options until S4 moves them to the key view. -->
  <svelte:fragment slot="key">
  <fieldset class="keyopts">
    <legend>Answer key</legend>
    <select
      aria-label="Answer key style"
      title="School key: an answer grid for multiple choice, then a table of short working with Ans:, as schools print it. Worked solutions: each question with its full solution."
      value={keyOpts.layout}
      on:change={setKeyLayout}
    >
      <option value="compact">School key</option>
      <option value="full">Worked solutions</option>
    </select>
    {#if keyOpts.layout === 'full'}
      <label>
        <input
          type="checkbox"
          aria-label="Answer key repeats each question"
          checked={keyOpts.show_question}
          on:change={(e) => setKeyOption('show_question', e.currentTarget.checked)}
        />
        question
      </label>
    {/if}
    <label>
      <input
        type="checkbox"
        aria-label="Answer key shows the marking scheme (M1, A1)"
        checked={keyOpts.show_scheme}
        on:change={(e) => setKeyOption('show_scheme', e.currentTarget.checked)}
      />
      M1/A1
    </label>
    {#if keyOpts.layout === 'compact'}
      <label>
        <input
          type="checkbox"
          aria-label="Answer key shows each question's marks"
          checked={keyOpts.show_marks}
          on:change={(e) => setKeyOption('show_marks', e.currentTarget.checked)}
        />
        marks
      </label>
      <label>
        <input
          type="checkbox"
          aria-label="Answer key shows the working for 1-mark questions"
          checked={keyOpts.one_mark_working}
          on:change={(e) => setKeyOption('one_mark_working', e.currentTarget.checked)}
        />
        1-mark working
      </label>
    {/if}
  </fieldset>
  </svelte:fragment>
</SidePanel>
</div>

{#if confirmRegen && regenInfo}
  <ConfirmDialog
    title="Regenerate unlocked questions?"
    body={regenBody}
    confirmLabel="Regenerate"
    onConfirm={() => {
      confirmRegen = false
      void regenerate()
    }}
    onCancel={() => (confirmRegen = false)}
  />
{/if}

<MathPopover />

{#if pickerAt !== undefined}
  <AddQuestion
    on:insert={(e) => insertQuestion(e.detail.question)}
    on:freeform={insertFreeformQuestion}
    on:close={() => (pickerAt = undefined)}
  />
{/if}

{#if unfilled}
  <PrintWarning
    questions={unfilled.questions}
    on:fill={fillPlaceholders}
    on:print={() => unfilled && download(unfilled.mode, true)}
    on:cancel={() => (unfilled = null)}
  />
{/if}

{#if previewHtml !== null}
  <div class="backdrop" role="presentation" on:click|self={() => (previewHtml = null)}>
    <div class="preview" role="dialog" aria-modal="true" aria-label="Print preview">
      <button class="close" aria-label="Close preview" on:click={() => (previewHtml = null)}
        >×</button
      >
      {#if pageSummary}
        <div class="pagesum" aria-label="Pages">
          <strong>{pageSummary.pages.length} page{pageSummary.pages.length === 1 ? '' : 's'}</strong>
          {#each pageSummary.pages as p (p.page)}
            <span>p{p.page}: {describePage(p)}</span>
          {/each}
          {#if pageSummary.warnings}
            <span class="warn" role="alert"
              >{pageSummary.warnings} question{pageSummary.warnings === 1 ? '' : 's'} had working
              space trimmed to fit a page</span
            >
          {/if}
        </div>
      {/if}
      <iframe title="Print preview" srcdoc={previewHtml} on:load={readPages}></iframe>
    </div>
  </div>
{/if}

<style>
  /* EXA-160: one sticky header, two rows (EditorBar, then the formatting toolbar). */
  .ehead {
    position: sticky;
    top: 0;
    z-index: 10;
    background: var(--page);
    border-bottom: 1px solid var(--line);
    font-size: 13px;
  }
  .tools {
    display: flex;
    align-items: center;
    gap: 2px;
    height: 44px;
    margin-top: var(--s2);
    padding: var(--s1) var(--s4) var(--s1) calc(var(--s4) - 4px);
    border-top: 1px solid var(--line-soft);
  }
  .tools .btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 30px;
    padding: 0 10px;
    border: 1px solid transparent;
    border-radius: var(--r-sm);
    background: transparent;
    color: var(--ink);
    font-size: 13px;
    font-weight: 500;
    white-space: nowrap;
  }
  .tools .icon-btn,
  .tools :global(.icon-btn) {
    display: inline-grid;
    place-items: center;
    flex: none;
    width: 32px;
    height: 32px;
    padding: 0;
    border: 1px solid transparent;
    border-radius: var(--r-sm);
    background: transparent;
    color: var(--ink-soft);
    font-size: 14px;
    cursor: pointer;
  }
  .tools :global(.styleselect) {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 30px;
    padding: 0 var(--s2);
    border: 1px solid transparent;
    border-radius: var(--r-sm);
    background: transparent;
    color: var(--ink-soft);
    font: inherit;
    font-size: 13px;
    white-space: nowrap;
    cursor: pointer;
  }
  .tools .btn:hover,
  .tools .icon-btn:hover,
  .tools :global(.icon-btn:hover),
  .tools :global(.styleselect:hover),
  .tools :global([aria-expanded='true']) {
    background: var(--wash);
    color: var(--ink);
  }
  .tools .icon-btn[aria-pressed='true'] {
    background: var(--verify-soft);
    color: var(--verify-ink);
  }
  .tools .icon-btn[aria-disabled='true'] {
    color: var(--ink-faint);
    opacity: 0.5;
    cursor: default;
  }
  .tools .icon-btn[aria-disabled='true']:hover {
    background: transparent;
  }
  .sep {
    flex: none;
    width: 1px;
    height: 20px;
    margin: 0 var(--s2);
    background: var(--line);
  }
  .tail {
    margin-left: auto;
  }
  button {
    font: inherit;
    font-size: 12.5px;
    border: 1px solid var(--line);
    background: var(--paper);
    color: var(--ink);
    border-radius: 6px;
    padding: 0.25rem 0.65rem;
    cursor: pointer;
  }
  button:disabled {
    opacity: 0.5;
    cursor: default;
  }
  .banner {
    margin: 0;
    padding: 0.5rem 1rem;
    background: var(--mark-soft);
    color: var(--mark);
    font-size: 13px;
  }
  .banner.note {
    background: var(--wash);
    color: var(--ink-soft);
  }
  .toast {
    position: fixed;
    left: 50%;
    bottom: var(--s6);
    z-index: 50;
    transform: translateX(-50%);
    display: flex;
    align-items: center;
    gap: var(--s2);
    padding: var(--s2) var(--s2) var(--s2) var(--s4);
    background: var(--ink);
    color: var(--on-accent);
    border-radius: var(--r-md);
    box-shadow: var(--shadow);
    font-size: 13.5px;
  }
  .toast button {
    font: inherit;
    font-weight: 600;
    padding: 4px var(--s2);
    border: 0;
    border-radius: var(--r-sm);
    background: none;
    color: var(--on-accent);
    text-decoration: underline;
    cursor: pointer;
  }
  .toast button:hover {
    background: color-mix(in srgb, var(--on-accent) 15%, transparent);
  }
  .loading {
    text-align: center;
    color: var(--ink-faint);
  }
  .hidden {
    display: none;
  }

  .desk :global(.qblock),
  .desk :global(.ffblock) {
    scroll-margin-top: calc(var(--bar-h, 0px) + 1rem); /* clear the sticky header */
  }
  /* The page in the middle, the side panel to its right (EXA-160). Narrower: the page takes
     what is left beside a fixed panel; below 900 px the panel stacks above the page. */
  .desk {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 210mm) minmax(260px, 1fr);
    gap: var(--s6);
    align-items: start;
    background: var(--desk);
    padding: var(--s6) var(--s4) 4rem;
    min-height: 100vh;
  }
  .main {
    grid-column: 2;
    min-width: 0;
  }
  .desk > :global(.panel) {
    grid-column: 3;
    justify-self: start;
    width: 100%;
    max-width: 300px;
  }
  @media (max-width: 1199px) {
    .desk {
      grid-template-columns: minmax(0, 1fr) 280px;
      gap: var(--s4);
    }
    .main {
      grid-column: 1;
    }
    .desk > :global(.panel) {
      grid-column: 2;
      max-width: none;
    }
  }
  @media (max-width: 899px) {
    .desk {
      grid-template-columns: minmax(0, 1fr);
    }
    .desk > :global(.panel) {
      grid-column: 1;
      grid-row: 1;
    }
    .main {
      grid-row: 2;
    }
  }
  .page {
    width: 210mm;
    max-width: 100%;
    min-height: 297mm;
    margin: 0 auto;
    background: var(--page);
    color: var(--ink);
    box-shadow: var(--shadow);
    padding: 18mm 20mm;
    box-sizing: border-box;
  }
  .title {
    width: 100%;
    border: none;
    outline: none;
    font-family: var(--serif);
    font-size: 1.9rem;
    font-weight: 600;
    background: transparent;
    color: inherit;
    padding: 0;
  }
  .sheetmeta {
    display: flex;
    justify-content: space-between;
    margin: 0.3rem 0 1.2rem;
    padding-bottom: 0.6rem;
    border-bottom: 2px solid var(--ink);
    font-size: 0.9rem;
  }
  .surface :global(.ProseMirror) {
    outline: none;
    min-height: 120mm;
    counter-reset: q var(--q-start, 0);
    font-family: var(--serif);
  }
  /* A question block (EXA-161): nothing at rest, a faint wash on hover, a green edge and ring
     when selected (QuestionBar sets .is-active). The ⋮⋮ handle sits in the left gutter. */
  .surface :global(.qblock) {
    counter-increment: q;
    position: relative;
    padding: var(--s3) var(--s3) var(--s3) var(--s2);
    margin: 0 -14px var(--s2);
    border: 1px solid transparent;
    border-radius: var(--r-md);
  }
  .surface :global(.qblock:hover) {
    background: color-mix(in srgb, var(--wash) 60%, transparent);
  }
  .surface :global(.qblock.is-active) {
    border-color: var(--verify);
    background: var(--page);
    box-shadow: 0 0 0 3px var(--verify-soft);
  }
  .surface :global(.qblock:focus-visible) {
    outline: none; /* .is-active is the focus ring */
  }
  .surface :global(.qblock.ProseMirror-selectednode) {
    outline: none;
  }
  .surface :global(.ffblock) {
    display: grid;
    grid-template-columns: 2rem 1fr;
    gap: 0.25rem;
  }
  .surface :global(.ff-num) {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  .surface :global(.ff-num::before) {
    content: counter(q) '.';
    font-family: var(--mono);
    font-weight: 600;
    color: var(--ink-soft);
  }
  .surface :global(.ff-row) {
    display: flex;
    gap: 0.5rem;
    align-items: baseline;
  }
  .surface :global(.ff-body) {
    flex: 1 1 auto;
    min-height: 1.6em;
  }
  .surface :global(.ff-body > :first-child) {
    margin-top: 0;
  }
  .surface :global(.ff-body > :last-child) {
    margin-bottom: 0;
  }
  .surface :global(.ff-marks) {
    flex: 0 0 auto;
    font-family: var(--mono);
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--mark);
  }
  .surface :global(.doc-image-node) {
    margin: 0.5rem 0;
    padding: 0;
    border-radius: 4px;
  }
  .surface :global(.doc-image-img) {
    display: block;
    height: auto;
    max-width: 100%;
  }
  .surface :global(.doc-image-node.selected) {
    outline: 2px solid var(--verify);
  }
  .surface :global(.doc-image-bar) {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.6rem;
    margin-top: 0.3rem;
    padding: 0.3rem 0.5rem;
    border: 1px solid var(--line);
    border-radius: 6px;
    background: var(--paper);
    font-family: var(--sans);
    font-size: 12px;
  }
  .surface :global(.doc-image-bar input) {
    font: inherit;
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 0.15rem 0.3rem;
    background: var(--page);
    color: var(--ink);
  }
  .surface :global(.doc-image-width) {
    width: 4rem;
  }
  .surface :global(.doc-image-bar button) {
    font: inherit;
    border: 1px solid var(--line);
    background: var(--paper);
    border-radius: 6px;
    padding: 0.15rem 0.5rem;
    cursor: pointer;
  }
  .surface :global(.doc-image-bar .danger) {
    color: var(--mark);
  }
  .surface :global(.math-node) {
    cursor: pointer;
    border-radius: 3px;
  }
  .surface :global(.math-node:hover),
  .surface :global(.math-node.ProseMirror-selectednode) {
    background: var(--verify-soft);
  }
  .surface :global(.section-block) {
    margin: 1.2rem 0 0.8rem;
    padding-bottom: 0.5rem;
    border-bottom: 1.5px solid var(--ink);
  }
  .surface :global(.section-row) {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.6rem;
  }
  .surface :global(.section-title-input) {
    flex: 1 1 14rem;
    font: inherit;
    font-size: 1.15rem;
    font-weight: 700;
    border: 1px dashed transparent;
    background: transparent;
    color: var(--ink);
  }
  .surface :global(.section-title-input:hover),
  .surface :global(.section-title-input:focus) {
    border-color: var(--line);
  }
  .surface :global(.section-field) {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 12px;
    color: var(--ink-soft);
  }
  .surface :global(.section-field select),
  .surface :global(.section-target-input) {
    font: inherit;
    font-size: 12.5px;
    border: 1px solid var(--line);
    border-radius: 6px;
    background: var(--paper);
    color: var(--ink);
  }
  .surface :global(.section-target-input) {
    width: 4rem;
  }
  .surface :global(.section-instructions-input) {
    display: block;
    width: 100%;
    margin-top: 0.4rem;
    font: inherit;
    font-size: 0.9rem;
    font-style: italic;
    border: 1px dashed transparent;
    background: transparent;
    color: var(--ink);
    resize: vertical;
  }
  .surface :global(.section-instructions-input:hover),
  .surface :global(.section-instructions-input:focus) {
    border-color: var(--line);
  }
  .surface :global(.section-summary) {
    margin: 0.3rem 0 0;
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--ink-soft);
  }
  .surface :global(.section-summary[data-state='over']),
  .surface :global(.section-summary[data-state='under']) {
    color: var(--mark, #b42318);
  }
  .surface :global(.ff-placeholder-hint) {
    margin: 0 0 0.3rem;
    font-size: 12.5px;
    font-style: italic;
    color: var(--mark, #b42318);
  }
  .surface :global(.ffblock.placeholder-slot .ff-body) {
    border: 1px dashed var(--line);
    border-radius: 6px;
  }
  /* the empty line itself is the tall target, so a click anywhere in the box lands in it */
  .surface :global(.ffblock.placeholder-slot .ff-body > p:first-child) {
    min-height: 2.2em;
    margin: 0;
  }
  .surface :global(.page-block) {
    margin: 1rem 0;
    padding: 0.7rem 0.9rem;
    border: 1.5px dashed var(--line);
    border-radius: 8px;
  }
  .surface :global(.page-block-title) {
    margin: 0 0 0.4rem;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--ink-soft);
  }
  .surface :global(.page-row) {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.6rem;
  }
  .surface :global(.page-row .page-block-title) {
    margin: 0;
  }
  .surface :global(.cover-grid) {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
    gap: 0.4rem 0.8rem;
  }
  .surface :global(.page-field) {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    font-size: 12px;
    color: var(--ink-soft);
  }
  .surface :global(.page-field.inline) {
    flex-direction: row;
    align-items: center;
    gap: 0.4rem;
    margin-top: 0.4rem;
  }
  .surface :global(.page-block input:not([type='checkbox'])),
  .surface :global(.page-block select),
  .surface :global(.cover-instructions-input) {
    font: inherit;
    font-size: 13px;
    padding: 0.2rem 0.4rem;
    border: 1px solid var(--line);
    border-radius: 6px;
    background: var(--paper);
    color: var(--ink);
  }
  .surface :global(.cover-instructions-input) {
    display: block;
    width: 100%;
    margin-top: 0.5rem;
    resize: vertical;
  }
  .surface :global(.blank-text-input) {
    flex: 1 1 14rem;
  }
  .surface :global(.page-block-note) {
    margin: 0.4rem 0 0;
    font-size: 12px;
    color: var(--ink-soft);
  }
  .surface :global(.page-break-marker) {
    border-top: 2px dashed var(--line);
    text-align: center;
    font-family: var(--mono);
    font-size: 11px;
    color: var(--ink-faint);
    margin: 1rem 0;
  }
  .surface :global(.ProseMirror-selectednode) {
    outline: 2px solid var(--verify);
    border-radius: 6px;
  }
  .plus {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.6rem;
    width: 100%;
    margin-top: 1rem;
    padding: 1.4rem;
    border: 2px dashed var(--line);
    border-radius: 10px;
    background: transparent;
    color: var(--ink-soft);
    font-size: 15px;
  }
  .plus:hover {
    border-color: var(--verify);
    color: var(--verify-ink);
    background: var(--verify-soft);
  }
  .plus-sign {
    font-size: 1.8rem;
    line-height: 1;
  }

  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba(25, 28, 33, 0.5);
    display: grid;
    place-items: center;
    z-index: 60;
  }
  .preview {
    position: relative;
    width: min(900px, 96vw);
    height: 90vh;
    background: var(--page);
    border-radius: 10px;
    overflow: hidden;
  }
  .preview {
    display: flex;
    flex-direction: column;
  }
  .preview iframe {
    flex: 1 1 auto;
    width: 100%;
    min-height: 0;
    border: none;
  }
  .pagesum {
    max-height: 5.5rem;
    overflow-y: auto;
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem 0.9rem;
    padding: 0.45rem 2.6rem 0.45rem 0.9rem;
    border-bottom: 1px solid var(--line);
    background: var(--paper-2);
    font-size: 12px;
    color: var(--ink-soft);
  }
  .pagesum .warn {
    color: var(--mark);
    font-weight: 600;
  }
  .close {
    position: absolute;
    right: 0.6rem;
    top: 0.4rem;
    z-index: 2;
    font-size: 1.2rem;
  }
</style>
