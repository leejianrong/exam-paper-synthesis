<script lang="ts">
  import { BlockSelectionGuard, insertBlockSafely } from './blockSelection'
  import { selectedSettingsBlock, settingsTransaction, settingsBlockPos, type SettingsBlock } from './blockSettings'
  import Icon from '../Icon.svelte'
  import Menu, { type MenuItem } from '../Menu.svelte'
  import ConfirmDialog from '../ConfirmDialog.svelte'
  import Dialog from '../Dialog.svelte'
  import MenuBar, { type BarMenu } from '../MenuBar.svelte'
  import { ariaKeys, keyLabel } from '../keys'
  import { navigate } from '../router'
  import EditorBar from './EditorBar.svelte'
  import CommandPalette from './CommandPalette.svelte'
  import MoveDialog from './MoveDialog.svelte'
  import ShortcutSheet from './ShortcutSheet.svelte'
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
  // to add questions, autosave, and the export/preview menu. The header's Paper | Answer key
  // switch shows the key, as it prints, in place of the page (EXA-162).
  import { onDestroy, onMount, tick as nextTick } from 'svelte'
  import { Editor } from '@tiptap/core'
  import StarterKit from '@tiptap/starter-kit'
  import { NodeSelection, TextSelection, type Selection } from '@tiptap/pm/state'

  import type { Question } from '../types'
  import type { BankItem } from '../api'
  import AddQuestion from './AddQuestion.svelte'
  import AnswerDialog from './AnswerDialog.svelte'
  import SaveToBankDialog from './SaveToBankDialog.svelte'
  import BankSwapDialog from './BankSwapDialog.svelte'
  import KeyView from './KeyView.svelte'
  import { answerWritten, keyNumbers } from './keyRows'
  import { withReviewed } from './inspector'
  import { createAutosaver, type Autosaver } from './autosave'
  import {
    buildDocument,
    freeformNode,
    ownBankNode,
    numberedNodes,
    paperOutline,
    totalMarks,
    type DocJSON,
    type DocumentRecord,
  } from './doc'
  import {
    copyDocument,
    deleteDocument,
    exportDocument,
    getDocument,
    listFolders,
    moveDocument,
    previewDocument,
    regeneratePaper,
    saveDocument,
    swapQuestion,
    unfilledDetail,
    type ExportMode,
    type Folder,
    type SwapMode,
  } from './docsApi'
  import { FreeformQuestion, QuestionDocument, insertFreeform } from './freeformQuestion'
  import { IMAGE_TYPES, uploadAsset } from './assets'
  import MathPopover from './MathPopover.svelte'
  import { openMathEditor } from './mathEditor'
  import { ImageBlock, ImageUpload, MathNode, uploadAndInsert } from './media'
  import { PageBreak } from './pageBreak'
  import { BlankPage, CoverPage, blankPageNode, coverNode } from './pages'
  import { isUnfilledPlaceholder, lastReport, reportSummary, unfilledPlaceholders } from './paperReport'
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
  import { GroupStem, insertStem } from './groupStem'
  import { loadQuota, type Quota } from '../session'
  import { TemplatedQuestion, questionNode } from './templatedQuestion'
  import {
    BlockShortcuts,
    GLOBAL_KEYS,
    commandsForBlock,
    globalShortcut,
    type Command,
    type GlobalCommand,
  } from './shortcuts'

  import ErrorNote from '../ErrorNote.svelte'
  import { canRetry, createFailedText, errorText } from '../errors'
  import PaperUnavailable from './PaperUnavailable.svelte'
  import EditorSkeleton from './EditorSkeleton.svelte'

  export let id: string

  let element: HTMLDivElement
  let editor: Editor | null = null
  let autosaver: Autosaver | null = null
  let unsubscribe: (() => void) | null = null

  let title = ''
  let loadError: unknown = null // why the paper didn't open (EXA-165)
  let loading = true
  let content: DocJSON = { type: 'doc', content: [] }
  let status: 'saved' | 'dirty' | 'saving' | 'conflict' | 'error' = 'saved'
  let pickerAt: number | null | undefined = undefined // undefined = closed, null = end
  let busy = ''
  let actionError = ''
  /** "Try again" for the failure in `actionError`, when the same request may work now. */
  let actionRetry: (() => void) | null = null
  /** Why the last save failed (the bar says "Not saved"; the strip says why and retries). */
  let saveError: unknown = null
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
  let folderId: string | null = null
  let titleInput: HTMLInputElement
  let panelTab: 'paper' | 'selection' = 'paper'
  /** The selected section or cover, whose settings the side panel shows (EXA-164). */
  let settingsBlock: SettingsBlock | null = null
  /** Bumps when the author selects a section or the cover; a selection that only moved with an
   *  edit above it (an insert, a delete, an undo) does not count. */
  let settingsPick = 0
  let lastSelection: Selection | null = null
  let confirmRegen = false
  let innerWidth = 1440
  /** Below 1024 px the toolbar's tail (lists, equation, image) moves into its ⋯ menu. */
  $: narrow = innerWidth < 1024
  /** Below 900 px the menu row folds into one "Menu" button. */
  $: compactMenus = innerWidth < 900

  // EXA-163: the menus' dialogs and the side panel's visibility (remembered per viewer).
  const PANEL_KEY = 'exam.editor.sidePanel'
  let panelShown = readPanelShown()
  let paletteOpen = false
  let paletteCommands: Command[] = []
  let sheetOpen = false
  let verifiedOpen = false
  let bankSwapFor: string | null = null // the block "Swap from your bank…" is picking for (EXA-33)
  let moveFolders: Folder[] | null = null
  let moveError = ''
  let confirmDelete = false
  let deleteError = ''
  let keyView: KeyView | undefined
  /** "Edit answer…": the own question whose answer is open. */
  let answerFor: string | null = null
  /** "Save to your bank…" (EXA-90): the own question being filed in the bank. */
  let bankSaveFor: string | null = null

  /** Show a failed action in plain words (EXA-165), with Try again when it may work now. */
  function failed(e: unknown, action: string, retry?: () => void) {
    showError(errorText(e, action), retry && canRetry(e) ? retry : null)
  }

  /** The one way to set (or clear, with '') the strip's error: its Try again goes with it, so
   *  a retry never outlives the failure it was for. */
  function showError(message: string, retry: (() => void) | null = null) {
    actionError = message
    actionRetry = retry
  }

  function readPanelShown(): boolean {
    try {
      return localStorage.getItem(PANEL_KEY) !== 'hidden'
    } catch {
      return true
    }
  }

  $: blocks = numberedNodes(content)
  $: marks = totalMarks(content)
  $: coverPresent = content.content?.[0]?.type === 'coverPage'
  // "Primary 6", "P6": the level a question saved from this paper starts at (EXA-90)
  $: paperLevel = /\b(?:P|Primary\s*)([56])\b/i.exec(String(coverPresent ? (content.content?.[0]?.attrs?.level ?? '') : ''))?.[1]
  $: bankSaveBlock = bankSaveFor === null ? undefined : blocks.find((b) => b.attrs?.block_id === bankSaveFor)
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

  /** The header's "N placeholders to write": the Paper tab's Generated paper group. */
  async function showPlaceholders() {
    if (!panelShown) await setPanel(true)
    panelTab = 'paper'
    await nextTick()
    const group = document.getElementById('panel-generated')
    group?.scrollIntoView?.({ block: 'nearest' })
    group?.focus()
  }

  async function setPanel(shown: boolean) {
    const hadFocus = !shown && !!document.activeElement?.closest('.panel')
    panelShown = shown
    try {
      localStorage.setItem(PANEL_KEY, shown ? 'shown' : 'hidden')
    } catch {
      // private window or blocked storage: the choice lasts for this visit
    }
    if (hadFocus) {
      await nextTick()
      editor?.view.focus()
    }
  }

  /** Paper > Paper settings…: the side panel's Paper tab, shown if it was hidden. */
  async function openPaperSettings() {
    if (!panelShown) await setPanel(true)
    panelTab = 'paper'
    await nextTick()
    document.getElementById('tab-paper')?.focus()
  }

  /** Paper > Cover page…: go to the cover's first field in the side panel, adding a cover first
   *  if there is none. */
  async function openCover() {
    if (!editor) return
    await toPaper()
    if (!coverPresent) editor.chain().insertContentAt(0, coverNode()).run()
    await openBlockSettings(0)
  }

  /** A section's or the cover's Edit button, or Alt+Enter on it (EXA-164): select the block and
   *  go to its first field in the side panel, showing the panel if it was hidden. */
  async function openBlockSettings(pos: number) {
    if (!editor) return
    const { state } = editor
    if (!state.doc.nodeAt(pos)) return
    editor.view.dispatch(state.tr.setSelection(NodeSelection.create(state.doc, pos)))
    if (!panelShown) await setPanel(true)
    panelTab = 'selection'
    await nextTick()
    const field = document.querySelector<HTMLElement>('#tabpanel-selection :is(input, textarea, select)')
    field?.scrollIntoView?.({ block: 'nearest' })
    field?.focus()
  }

  /** A change in the side panel's section or cover settings. */
  function setSettingsAttrs(attrs: Record<string, unknown>) {
    // during a swap or regenerate the fields are disabled; an edit then could be overwritten
    if (!editor || !settingsBlock || opInFlight) return
    const pos = settingsBlockPos(editor.state.doc, settingsBlock)
    if (pos !== null) editor.view.dispatch(settingsTransaction(editor.state, pos, attrs))
  }

  /** The header's Paper | Answer key switch, View > Paper / Answer key and Ctrl+Alt+K (EXA-162).
   *  Each view keeps its own scroll position; switching to the key with a question selected
   *  goes to that question's row instead. */
  let view: 'paper' | 'key' = 'paper'
  const viewScroll: Record<'paper' | 'key', number> = { paper: 0, key: 0 }
  async function showView(to: 'paper' | 'key') {
    if (to === view) return
    viewScroll[view] = window.scrollY
    view = to
    await nextTick()
    if (to === 'key') {
      document.querySelector<HTMLElement>('.keyview')?.focus({ preventScroll: true })
      const at = selectedId ? blocks.findIndex((b) => b.attrs?.block_id === selectedId) : -1
      if (at < 0 || !keyView?.scrollToQuestion(start + at, barH)) window.scrollTo?.({ top: viewScroll.key })
    } else {
      editor?.view.focus()
      window.scrollTo?.({ top: viewScroll.paper })
    }
  }

  const toggleView = () => void showView(view === 'key' ? 'paper' : 'key')

  async function openMove() {
    moveError = ''
    try {
      moveFolders = await listFolders()
    } catch (e) {
      failed(e, "Couldn't list your folders", () => void openMove())
    }
  }

  async function moveTo(folder: string | null) {
    if (busy) return // another operation (an export, say) owns busy until it ends
    moveError = ''
    busy = 'move'
    try {
      await moveDocument(id, folder)
      const name = moveFolders?.find((f) => f.id === folder)?.name ?? null
      folderId = folder
      folderName = name
      moveFolders = null
      notice = name ? `Moved to ${name}.` : 'Moved out of its folder: the paper is unfiled.'
    } catch (e) {
      moveError = errorText(e, "The paper wasn't moved")
    } finally {
      busy = ''
    }
  }

  /** Paper > Make a copy: a new paper with this one's content and settings, opened at once. */
  async function makeCopy() {
    const ed = editor
    if (!ed || busy) return
    busy = 'copy'
    showError('')
    try {
      await autosaver?.flush()
      const document = buildDocument(title, ed.getJSON() as DocJSON, $paperSettings)
      const rec = await copyDocument(id, { document, folder_id: folderId })
      navigate(`/docs/${rec.id}`)
    } catch (e) {
      // no Try again: the copy may have been made although the reply was lost
      showError(createFailedText(e, "Couldn't make a copy"))
    } finally {
      busy = ''
    }
  }

  async function deletePaper() {
    if (busy) return
    busy = 'delete'
    deleteError = ''
    try {
      await deleteDocument(id)
      autosaver?.dispose() // nothing left to save to
      confirmDelete = false
      navigate('/')
    } catch (e) {
      deleteError = errorText(e, "The paper wasn't deleted")
    } finally {
      busy = ''
    }
  }

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

  function setKeyLayout(layout: KeyLayout) {
    // each style starts from its own defaults: the school key bare, worked solutions with M/A lines
    const defaults =
      layout === 'compact'
        ? { show_scheme: false, show_marks: false, one_mark_working: false }
        : { show_scheme: true, show_question: true }
    paperSettings.update((s) => ({ ...s, key_options: { ...s.key_options, ...defaults, layout } }))
    scheduleSave()
  }

  const setInKey = (blockId: string, included: boolean) =>
    setBlockAttrs(blockId, ['templatedQuestion', 'freeformQuestion'], { in_key: included })

  // What the key view names: the numbers it prints, the questions left out, and the teacher's
  // own questions (their answers are written for the key).
  $: keyNums = keyNumbers(blocks, start)
  // any edit to the paper, its settings or its title makes the key on screen out of date
  $: keyRevision = [content, $paperSettings, title]
  $: leftOut = blocks.flatMap((b, i) =>
    b.attrs?.in_key === false ? [{ n: start + i, blockId: String(b.attrs?.block_id) }] : [],
  )
  $: ownAnswers = blocks.flatMap((b, i) =>
    b.type === 'freeformQuestion' && b.attrs?.in_key !== false && !isUnfilledPlaceholder(b)
      ? [{ n: start + i, blockId: String(b.attrs?.block_id), written: answerWritten(b) }]
      : [],
  )
  $: answerAt = answerFor === null ? -1 : blocks.findIndex((b) => b.attrs?.block_id === answerFor)

  /** The key view's key: the paper as saved, so pending edits are saved first. */
  async function loadKey(): Promise<string> {
    await autosaver?.flush()
    if (status === 'conflict') throw new Error('This paper changed in another tab or window. Reload to get the latest version.')
    if (status === 'error') throw new Error('Your latest changes are not saved yet.')
    return previewDocument(id, 'key')
  }

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

  onMount(() => {
    // capture: ahead of the editor's own keys (its Ctrl+Enter line break, say)
    window.addEventListener('keydown', onGlobalKey, true)
    void loadQuota().then((q) => (quota = q))
    void openPaper()
  })

  /** Load the paper and start the editor; a failure shows a page of its own (EXA-165). */
  async function openPaper() {
    loading = true
    loadError = null
    // a retry after a load that failed part way starts clean: no second editor or autosaver
    unsubscribe?.()
    autosaver?.dispose()
    editor?.destroy()
    unsubscribe = null
    autosaver = null
    editor = null
    // An editor whose constructor threw leaves its page behind. Svelte renders nothing inside
    // this element (TipTap owns it), so clearing it can't confuse the runtime.
    // eslint-disable-next-line svelte/no-dom-manipulating
    element?.replaceChildren()
    try {
      const rec = await getDocument(id)
      title = rec.document.title
      paperSettings.set({
        marks_placement: DEFAULT_PLACEMENT,
        ...(rec.document.settings ?? {}),
      })
      content = rec.document.content
      folderId = rec.folder_id ?? null
      if (rec.folder_id) {
        const folder = rec.folder_id
        void listFolders()
          .then((fs) => (folderName = fs.find((f) => f.id === folder)?.name ?? null))
          .catch(() => undefined)
      }
      autosaver = createAutosaver({
        initialVersion: rec.version,
        save: (doc, base) => saveDocument(id, doc, base),
        onError: (e) => (saveError = e),
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
            onError: (m: string) => showError(m),
          }),
          PageBreak,
          Section.configure({ onEdit: (pos: number) => void openBlockSettings(pos) }),
          CoverPage.configure({ onEdit: (pos: number) => void openBlockSettings(pos) }),
          BlankPage,
          GroupStem,
          BlockSelectionGuard,
          BlockShortcuts,
          FreeformQuestion.configure({
            onAddBelow: (pos: number) => (pickerAt = pos),
            onSwap: swapBlock,
            onDeleted: questionDeleted,
            onEditAnswer: (blockId: string) => (answerFor = blockId),
            onSaveToBank: (blockId: string) => (bankSaveFor = blockId),
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
          // the question went (deleted, undone): its open answer closes
          if (answerFor && !numberedNodes(content).some((b) => b.attrs?.block_id === answerFor)) answerFor = null
          scheduleSave()
        },
        onTransaction: ({ editor: e, transaction }) => {
          tick += 1
          const sel = e.state.selection
          const moved = !lastSelection || !sel.eq(lastSelection.map(e.state.doc, transaction.mapping))
          lastSelection = sel
          settingsBlock = selectedSettingsBlock(e.state)
          if (moved && settingsBlock) settingsPick += 1
          // The toast's Undo undoes only the deletion it reports: any later change (or a
          // Ctrl+Z) closes it. The deletion itself comes before `questionDeleted`.
          if (deleted && transaction.docChanged) closeDeleted()
        },
      })
      startWithTextCursor(editor)
      content = editor.getJSON() as DocJSON
      tick += 1 // the toolbar reads the opening selection, before any transaction
    } catch (e) {
      loadError = e
    } finally {
      loading = false
    }
  }

  onDestroy(() => {
    window.removeEventListener('keydown', onGlobalKey, true)
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

  function closeDeleted() {
    deleted = false
    clearTimeout(deletedTimer)
  }

  function undoDelete() {
    if (!deleted) return
    closeDeleted()
    editor?.chain().focus().undo().run()
  }

  function trackBlock(e: Event) {
    // A menu row removes itself before its click bubbles here: that is no move out of the block.
    if (!(e.target as Node).isConnected) return
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
    if (q.freeform) {
      // the teacher's own question goes in as they wrote it, to edit like any of theirs (EXA-90)
      insertFreeform(editor, insertionPoint(editor), ownBankNode(q))
      pickerAt = undefined
      return
    }
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
    showError('')
    await uploadAndInsert(editor, files, {
      upload: (f) => uploadAsset(f, f.name),
      onError: (m) => showError(m),
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

  /** Anything that puts something into the paper shows the paper first (EXA-162): from the key
   *  view it would otherwise land, unseen, in the hidden page. On the paper it runs at once. */
  function onPaper(run: () => void) {
    if (view === 'paper') run()
    else void showView('paper').then(run)
  }
  const toPaper = () => new Promise<void>((done) => onPaper(done))

  /** Run an editor command from a menu and put the caret back in the paper at once. */
  function inPaper(run: (e: Editor) => void) {
    onPaper(() => {
      const e = editor
      if (!e) return
      run(e)
      e.view.focus()
    })
  }

  /** + Question, Insert > Question…, Ctrl+Enter: the picker, over the paper. */
  const addQuestion = () => onPaper(() => (pickerAt = null))
  const pickImage = () => onPaper(() => fileInput.click())

  const styleItems: MenuItem[] = [
    { label: 'Normal text', onSelect: () => inPaper((e) => e.chain().setParagraph().run()) },
    ...([1, 2, 3] as const).map((level) => ({
      label: `Heading ${level}`,
      onSelect: () => inPaper((e) => e.chain().setHeading({ level }).run()),
    })),
  ]

  // The toolbar's ⋯ holds its tail (lists, equation, image) on a narrow window only; the
  // page-level inserts live in the Insert menu (EXA-163).
  $: moreItems = [
    { label: 'Bulleted list', icon: 'bullets', onSelect: () => inPaper((e) => e.chain().toggleBulletList().run()) },
    { label: 'Numbered list', icon: 'numbers', onSelect: () => inPaper((e) => e.chain().toggleOrderedList().run()) },
    {
      label: 'Equation',
      icon: 'sigma',
      shortcut: GLOBAL_KEYS.equation,
      disabled: !act.inText,
      hint: act.inText ? undefined : EQUATION_OFF,
      onSelect: addEquation,
    },
    { label: 'Image', icon: 'image', onSelect: () => pickImage() },
  ] satisfies MenuItem[]

  // EXA-163: the Paper / Insert / View / Help menus under the title (UI-REDESIGN 4.2).
  $: idle = !busy
  $: barMenus = [
    {
      label: 'Paper',
      items: [
        { label: 'Paper settings…', icon: 'settings', onSelect: openPaperSettings },
        {
          label: 'Cover page…',
          icon: 'cover',
          hint: coverPresent ? 'Go to the cover page' : 'Add a cover page at the start and fill it in',
          onSelect: openCover,
        },
        {
          label: regenInfo ? `Regenerate ${plural(regenInfo.unlocked, 'unlocked question')}…` : 'Regenerate unlocked questions…',
          icon: 'swap',
          disabled: !regenInfo || !idle,
          hint: regenInfo ? 'New questions in every unlocked place; locked ones stay' : 'Only a generated paper can be regenerated',
          onSelect: () => (confirmRegen = true),
        },
        { label: 'Rename', icon: 'pen', separator: true, onSelect: rename },
        { label: 'Move to folder…', icon: 'folder', disabled: !idle, onSelect: () => void openMove() },
        { label: 'Make a copy', icon: 'copy', disabled: !idle, onSelect: () => void makeCopy() },
        {
          label: 'Delete paper…',
          icon: 'trash',
          danger: true,
          separator: true,
          disabled: !idle,
          onSelect: () => (confirmDelete = true),
        },
      ],
    },
    {
      label: 'Insert',
      items: [
        { label: 'Question…', icon: 'plus', shortcut: GLOBAL_KEYS.addQuestion, onSelect: () => addQuestion() },
        {
          label: 'Section',
          icon: 'section',
          onSelect: () => inPaper((e) => insertBlockSafely(e, { type: 'section', attrs: { title: '' } })),
        },
        {
          label: 'Shared stem',
          icon: 'stem',
          hint: 'Text or a figure that the next questions all use ("Use the table below to answer Questions 12 and 13")',
          onSelect: () => inPaper((e) => insertStem(e)),
        },
        {
          label: 'Cover page',
          icon: 'cover',
          disabled: coverPresent,
          hint: coverPresent ? 'The paper already has a cover page' : 'Add a cover page at the start',
          onSelect: () => inPaper((e) => e.chain().insertContentAt(0, coverNode()).run()),
        },
        {
          label: 'Blank or rough-work page',
          icon: 'blankpage',
          onSelect: () => inPaper((e) => insertBlockSafely(e, blankPageNode())),
        },
        {
          label: 'Page break',
          icon: 'pagebreak',
          onSelect: () => inPaper((e) => insertBlockSafely(e, { type: 'pageBreak' })),
        },
        { label: 'Image…', icon: 'image', separator: true, onSelect: () => pickImage() },
        {
          label: 'Equation',
          icon: 'sigma',
          shortcut: GLOBAL_KEYS.equation,
          disabled: !act.inText,
          hint: act.inText ? undefined : EQUATION_OFF,
          onSelect: () => onPaper(addEquation),
        },
      ],
    },
    {
      label: 'View',
      items: [
        { label: 'Paper', icon: 'blankpage', checked: view === 'paper', onSelect: () => void showView('paper') },
        {
          label: 'Answer key',
          icon: 'key',
          shortcut: GLOBAL_KEYS.answerKey,
          checked: view === 'key',
          onSelect: () => void showView('key'),
        },
        {
          label: 'Preview pages',
          icon: 'eye',
          shortcut: GLOBAL_KEYS.preview,
          separator: true,
          disabled: !idle,
          onSelect: () => void preview('full'),
        },
        {
          label: 'Show side panel',
          shortcut: GLOBAL_KEYS.panel,
          checked: panelShown,
          onSelect: () => void setPanel(!panelShown),
        },
      ],
    },
    {
      label: 'Help',
      items: [
        { label: 'Keyboard shortcuts', icon: 'keyboard', shortcut: GLOBAL_KEYS.sheet, onSelect: () => (sheetOpen = true) },
        { label: 'What “verified” means', icon: 'info', onSelect: () => (verifiedOpen = true) },
      ],
    },
  ] satisfies BarMenu[]

  /** Everything the palette can run now: the selected question's rows, then every menu row
   *  and the exports. Rows that don't apply (disabled) are left out. */
  function collectCommands(): Command[] {
    const block = selectedId ? element?.querySelector(`[data-block-id="${CSS.escape(selectedId)}"]`) : null
    const rows: Command[] = commandsForBlock(block)
    for (const m of barMenus) {
      for (const item of m.items as MenuItem[]) {
        if (item.disabled) continue
        const label = item.checked ? item.label.replace(/^Show/, 'Hide') : item.label
        rows.push({ label, group: m.label, shortcut: item.shortcut, run: item.onSelect })
      }
    }
    if (!busy) {
      rows.push(
        { label: 'Export student paper (PDF)', group: 'Export', run: () => void download('student') },
        ...(blocks.length ? [{ label: 'Export answer key (PDF)', group: 'Export', run: () => void download('key') }] : []),
        { label: 'Export paper and key together (PDF)', group: 'Export', run: () => void download('full') },
      )
    }
    return rows
  }

  function openPalette() {
    paletteCommands = collectCommands()
    paletteOpen = true
  }

  async function runCommand(c: Command) {
    paletteOpen = false
    await nextTick() // the palette is gone and focus is back where it was
    c.run()
  }

  /** The editor-wide shortcuts (shortcuts.ts GLOBAL_KEYS). Inside the editor Ctrl+P previews the
   *  paper instead of printing this screen. */
  function onGlobalKey(e: KeyboardEvent) {
    if (loading || loadError || !editor) return
    const t = e.target as HTMLElement | null
    const cmd = globalShortcut(e, !!t?.matches?.('input, textarea, select'))
    if (!cmd) return
    e.preventDefault()
    // an open dialog (the picker, a confirmation, the palette itself) keeps the keyboard
    if (document.querySelector('[aria-modal="true"]') || busy === 'paper') return
    e.stopPropagation()
    runGlobal(cmd)
  }

  function runGlobal(cmd: GlobalCommand) {
    if (cmd === 'palette') openPalette()
    else if (cmd === 'addQuestion') addQuestion()
    else if (cmd === 'answerKey') toggleView()
    else if (cmd === 'preview') {
      if (!busy) void preview('full')
    } else if (cmd === 'panel') void setPanel(!panelShown)
    else if (cmd === 'sheet') sheetOpen = true
    else if (cmd === 'equation') onPaper(() => act.inText && addEquation())
  }

  async function download(mode: ExportMode, allowPlaceholders = false) {
    busy = `export-${mode}`
    showError('')
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
      else failed(e, "Couldn't export the PDF", () => void download(mode, allowPlaceholders))
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
    action: string,
    retry: () => void,
  ) {
    const ed = editor
    if (!ed || !autosaver || busy) return
    busy = 'paper'
    showError('')
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
      failed(e, action, retry)
    } finally {
      opInFlight = false
      ed.setEditable(true, false)
      busy = ''
      if (editedDuringOp) scheduleSave()
    }
  }

  async function swapBlock(blockId: string, mode: SwapMode, bankId?: string): Promise<void> {
    if (mode === 'bank' && !bankId) {
      bankSwapFor = blockId // the picker asks which bank question, then comes back here
      return
    }
    await paperOp(
      (base) => swapQuestion(id, blockId, mode, base, bankId),
      swapNotice,
      "The question wasn't swapped",
      () => void swapBlock(blockId, mode, bankId),
    )
    // The swapped block is selected; give the editor focus back (the menu that asked is gone),
    // so its pill shows and R swaps again (EXA-161).
    await nextTick()
    if (editor && (!document.activeElement || document.activeElement === document.body)) editor.view.focus()
  }

  // The bank list is worked out on the saved paper, so a question just inserted (or a block just
  // added) must be saved first, or it is offered again (or not found).
  async function saveForBank() {
    await autosaver?.flush()
    if (status === 'conflict' || status === 'error') {
      throw new Error('Your latest changes are not saved yet. Try again in a moment.')
    }
  }

  function pickFromBank(item: BankItem) {
    const blockId = bankSwapFor
    bankSwapFor = null
    if (blockId) void swapBlock(blockId, 'bank', item.id)
  }

  function regenerate(): Promise<void> {
    return paperOp(
      (base) => regeneratePaper(id, base),
      regenerateNotice,
      "The paper wasn't regenerated",
      () => void regenerate(),
    )
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
    showError('')
    pageSummary = null
    readToken++
    try {
      await autosaver?.flush()
      previewHtml = await previewDocument(id, mode)
    } catch (e) {
      failed(e, "Couldn't open the preview", () => void preview(mode))
    } finally {
      busy = ''
    }
  }
</script>

<svelte:window on:beforeunload={onBeforeUnload} bind:innerWidth />

<header class="ehead" bind:clientHeight={barH} inert={busy === 'paper'} class:hidden={loading || !!loadError}>
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
    {placeholdersLeft}
    onShowPlaceholders={showPlaceholders}
    onPreview={() => preview('full')}
    onExport={(mode) => download(mode)}
    onRename={rename}
    {view}
    onView={(v) => void showView(v)}
  >
    {#snippet menus()}<MenuBar menus={barMenus} compact={compactMenus} />{/snippet}
  </EditorBar>
  <!-- Clicking a tool must not take focus from the page (like Word/Docs): the editor keeps its
       caret, so keys typed right after a click go to the paper, not the button (a space would
       "press" it again; TipTap's focus() only refocuses a frame later). Keyboard use is unaffected. -->
  <div
    class="tools"
    role="toolbar"
    aria-label="Formatting"
    tabindex="-1"
    on:mousedown|preventDefault>
    <button
      class="btn quiet"
      title="Add a question ({keyLabel(GLOBAL_KEYS.addQuestion)})"
      aria-keyshortcuts={ariaKeys(GLOBAL_KEYS.addQuestion)}
      on:click={() => addQuestion()}><Icon name="plus" />Question</button
    >
    <button
      class="btn quiet"
      title="Insert a section"
      on:click={() => inPaper((e) => insertBlockSafely(e, { type: 'section', attrs: { title: '' } }))}
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
    {#if view === 'paper'}
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
        title={act.inText ? `Equation (${keyLabel(GLOBAL_KEYS.equation)})` : EQUATION_OFF}
        aria-keyshortcuts={ariaKeys(GLOBAL_KEYS.equation)}
        aria-disabled={!act.inText}
        on:click={() => act.inText && addEquation()}><Icon name="sigma" /></button
      >
      <button class="icon-btn" aria-label="Image" title="Insert image" on:click={() => fileInput.click()}
        ><Icon name="image" /></button
      >
    {/if}
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
    {#if narrow && view === 'paper'}
      <span class="tail">
        <Menu items={moreItems} label="More tools" align="end" triggerClass="icon-btn" triggerTitle="More tools">
          {#snippet trigger()}<Icon name="more" />{/snippet}
        </Menu>
      </span>
    {/if}
  </div>
</header>

{#if status === 'conflict'}
  <p class="banner" role="alert">
    This paper changed in another tab or window. Your latest edits were not saved.
    <button on:click={() => location.reload()}>Reload</button>
  </p>
{/if}
{#if status === 'error'}
  <ErrorNote
    strip
    message={errorText(saveError, "Your latest changes aren't saved")}
    onRetry={canRetry(saveError) ? () => void autosaver?.flush() : null}
  />
{/if}
{#if actionError}<ErrorNote strip message={actionError} onRetry={actionRetry} />{/if}
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
  <EditorSkeleton />
{:else if loadError}
  <PaperUnavailable error={loadError} onRetry={() => void openPaper()} />
{/if}

<div
  class="desk"
  class:nopanel={!panelShown}
  class:hidden={loading || !!loadError}
  style="--bar-h:{barH}px"
  inert={busy === 'paper'}
  aria-busy={busy === 'paper'}
>
<div class="main">
  <div class="page" class:hidden={view !== 'paper'}>
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

  <div class:hidden={view !== 'key'}>
    <KeyView
      bind:this={keyView}
      active={view === 'key' && !loading && !loadError}
      revision={keyRevision}
      paused={busy === 'paper'}
      load={loadKey}
      empty={blocks.length === 0}
      options={keyOpts}
      numbers={keyNums}
      {leftOut}
      own={ownAnswers}
      onStyle={setKeyLayout}
      onOption={setKeyOption}
      onInclude={(blockId) => setInKey(blockId, true)}
      onEditAnswer={(blockId) => (answerFor = blockId)}
      onKey={onGlobalKey}
    />
  </div>
</div>
{#if panelShown}
<SidePanel
  bind:tab={panelTab}
  context={settingsBlock}
  pick={settingsPick}
  locked={busy === 'paper'}
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
  on:blockattrs={(e) => setSettingsAttrs(e.detail)}
  on:done={() => editor?.view.focus()}
/>

{/if}
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

{#if confirmDelete}
  <ConfirmDialog
    title="Delete this paper?"
    body={`“${title || 'Untitled paper'}” and its answer key are deleted for good. This can't be undone.`}
    confirmLabel="Delete paper"
    danger
    busy={busy === 'delete'}
    error={deleteError}
    onConfirm={() => void deletePaper()}
    onCancel={() => {
      confirmDelete = false
      deleteError = ''
    }}
  />
{/if}

{#if moveFolders}
  <MoveDialog
    folders={moveFolders}
    current={folderId}
    busy={busy === 'move'}
    error={moveError}
    onMove={(f) => void moveTo(f)}
    onClose={() => (moveFolders = null)}
  />
{/if}

{#if paletteOpen}
  <CommandPalette commands={paletteCommands} onRun={runCommand} onClose={() => (paletteOpen = false)} />
{/if}

{#if sheetOpen}
  <ShortcutSheet onClose={() => (sheetOpen = false)} />
{/if}

{#if answerFor !== null && answerAt >= 0}
  <AnswerDialog
    number={start + answerAt}
    block={blocks[answerAt]}
    onAnswer={(answer) => answerFor && setAnswer(answerFor, answer)}
    onPartAnswer={(index, answer) => answerFor && setPartAnswer(answerFor, index, answer)}
    onError={(m) => showError(m)}
    onClose={() => (answerFor = null)}
  />
{/if}

{#if bankSaveFor !== null && bankSaveBlock}
  <SaveToBankDialog
    block={bankSaveBlock}
    level={paperLevel ? `P${paperLevel}` : ''}
    onSaved={({ status, id: bankId }) => {
      if (bankSaveFor) setBlockAttrs(bankSaveFor, ['freeformQuestion'], { bank_id: bankId })
      notice = status === 'replaced' ? 'Updated the copy in your bank.' : 'Saved to your bank.'
      bankSaveFor = null
    }}
    onClose={() => (bankSaveFor = null)}
  />
{/if}

{#if verifiedOpen}
  <Dialog title="What “verified” means" width="30rem" onClose={() => (verifiedOpen = false)}>
    <div class="verified">
      <p>
        A question the app generates is <strong>verified</strong>: a program works out its answer from the numbers
        printed in it. The answer in the key is the solution to exactly the question on the paper.
      </p>
      <p>
        Questions you write yourself, edit as your own text, or import are <strong>not verified</strong>. The app
        prints them as they are, so check their answers yourself. So is a generated question whose text, figure
        or worked answer is no longer what the app makes for its numbers (changed by hand, or saved before the app
        changed how it words that question).
      </p>
      <p>Verified means the maths is right. It does not mean the question suits your class: read the paper before you print it.</p>
    </div>
  </Dialog>
{/if}

<MathPopover />

{#if pickerAt !== undefined}
  <AddQuestion
    on:insert={(e) => insertQuestion(e.detail.question)}
    on:freeform={insertFreeformQuestion}
    on:close={() => (pickerAt = undefined)}
  />
{/if}

{#if bankSwapFor}
  <BankSwapDialog
    docId={id}
    blockId={bankSwapFor}
    ready={saveForBank}
    onPick={pickFromBank}
    onClose={() => (bankSwapFor = null)}
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
  .hidden,
  .desk.hidden {
    /* .desk sets its own display further down: this must win over it */
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
  /* View > Show side panel off (EXA-163): the page gets its full A4 width at every size. */
  .desk.nopanel {
    grid-template-columns: minmax(0, 1fr) minmax(0, 210mm) minmax(0, 1fr);
    column-gap: 0;
  }
  .desk.nopanel > .main {
    grid-column: 2;
    grid-row: auto;
  }
  .verified p {
    margin: 0 0 var(--s3);
    line-height: 1.5;
    color: var(--ink-soft);
  }
  .verified p:last-child {
    margin-bottom: 0;
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
  /* A section is a compact header and the cover a compact card; their settings edit in the side
     panel (EXA-164). A click selects the block, Edit (or Alt+Enter) goes to its fields. */
  .surface :global(.section-block) {
    margin: 1.2rem 0 0.8rem;
    padding: 0.2rem 0 0.4rem;
    border-bottom: 1.5px solid var(--ink);
    cursor: pointer;
  }
  .surface :global(.section-head),
  .surface :global(.cover-head) {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.25rem 0.75rem;
  }
  .surface :global(.section-title) {
    margin: 0;
    font-size: 1.15rem;
    font-weight: 700;
  }
  .surface :global(.section-title.untitled) {
    font-weight: 600;
    color: var(--ink-faint);
  }
  .surface :global(.section-summary) {
    font-size: 12.5px;
    font-weight: 600;
    color: var(--ink-soft);
  }
  .surface :global(.section-summary[data-state='over']),
  .surface :global(.section-summary[data-state='under']) {
    color: var(--mark);
  }
  .surface :global(.section-cues) {
    font-size: 12px;
    color: var(--ink-faint);
  }
  .surface :global(.section-instructions) {
    margin: 0.3rem 0 0;
    font-size: 0.9rem;
    color: var(--ink-soft);
  }
  /* A shared stem (EXA-90): its lead line is derived; its questions carry a bar down the left. */
  .surface :global(.group-stem-block) {
    margin: var(--s3) 0 var(--s2);
    padding: var(--s2) var(--s3);
    border-left: 3px solid var(--line);
    background: color-mix(in srgb, var(--wash) 50%, transparent);
    border-radius: 0 var(--r-md) var(--r-md) 0;
  }
  .surface :global(.group-head) {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.25rem 0.75rem;
  }
  .surface :global(.group-lead) {
    margin: 0;
    font-weight: 600;
  }
  .surface :global(.group-lead.empty) {
    font-weight: 500;
    color: var(--ink-faint);
  }
  .surface :global(.group-controls) {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 12.5px;
    color: var(--ink-soft);
  }
  .surface :global(.group-btn) {
    min-width: 1.6rem;
    padding: 0.1rem 0.45rem;
    border: 1px solid var(--line);
    border-radius: var(--r-sm, 4px);
    background: var(--page);
    color: var(--ink);
    font: inherit;
    cursor: pointer;
  }
  .surface :global(.group-btn:disabled) {
    opacity: 0.45;
    cursor: default;
  }
  .surface :global(.group-btn:focus-visible) {
    outline: 2px solid var(--verify);
    outline-offset: 1px;
  }
  .surface :global(.group-body > :first-child) {
    margin-top: var(--s1, 0.25rem);
  }
  .surface :global(.in-group) {
    box-shadow: inset 3px 0 0 var(--line);
  }
  .surface :global(.cover-block) {
    margin: 0 0 1.2rem;
    padding: 0.6rem 0.9rem 0.9rem;
    border: 1px solid var(--line);
    border-radius: 8px;
    cursor: pointer;
  }
  .surface :global(.cover-caption) {
    margin: 0;
    font-size: 12px;
    color: var(--ink-faint);
  }
  .surface :global(.cover-lines) {
    text-align: center;
  }
  .surface :global(.cover-line) {
    margin: 0.15rem 0 0;
    color: var(--ink-soft);
  }
  .surface :global(.cover-line:first-child) {
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--ink);
  }
  .surface :global(.cover-line.empty) {
    font-size: inherit;
    font-weight: 400;
    color: var(--ink-faint);
  }
  /* Edit: quiet at rest, shown on hover, focus or when the block is selected; always on touch. */
  .surface :global(.block-edit) {
    margin-left: auto;
    align-self: center;
    height: 28px;
    padding: 0 var(--s2);
    border: 0;
    border-radius: var(--r-sm);
    background: none;
    color: var(--ink-soft);
    font: inherit;
    font-size: 12.5px;
    font-weight: 600;
    cursor: pointer;
    opacity: 0;
  }
  .surface :global(.block-edit:hover) {
    background: var(--wash);
    color: var(--ink);
  }
  .surface :global(:is(.section-block, .cover-block):hover .block-edit),
  .surface :global(.ProseMirror-selectednode .block-edit),
  .surface :global(.block-edit:focus-visible) {
    opacity: 1;
  }
  @media (hover: none) {
    .surface :global(.block-edit) {
      opacity: 1;
    }
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
  .surface :global(.page-field) {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    font-size: 12px;
    color: var(--ink-soft);
  }
  .surface :global(.page-block input),
  .surface :global(.page-block select) {
    font: inherit;
    font-size: 13px;
    padding: 0.2rem 0.4rem;
    border: 1px solid var(--line);
    border-radius: 6px;
    background: var(--paper);
    color: var(--ink);
  }
  .surface :global(.blank-text-input) {
    flex: 1 1 14rem;
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
  .surface :global(.section-block.ProseMirror-selectednode) {
    outline-offset: 4px;
    border-radius: 0;
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
