<script lang="ts">
  // The WYSIWYG page (W1c): an A4-width column of rich text and question blocks, a "+"
  // to add questions, the answer key below, autosave, and the export/preview menu.
  import { onDestroy, onMount } from 'svelte'
  import { Editor } from '@tiptap/core'
  import StarterKit from '@tiptap/starter-kit'
  import type { Question } from '../types'
  import AddQuestion from './AddQuestion.svelte'
  import AccountChip from './AccountChip.svelte'
  import AnswerKey from './AnswerKey.svelte'
  import Inspector from './Inspector.svelte'
  import { createAutosaver, type Autosaver } from './autosave'
  import { buildDocument, freeformNode, numberedNodes, totalMarks, type DocJSON } from './doc'
  import {
    ApiError,
    exportDocument,
    getDocument,
    previewDocument,
    saveDocument,
    type ExportMode,
  } from './docsApi'
  import { FreeformQuestion, QuestionDocument, insertFreeform } from './freeformQuestion'
  import { IMAGE_TYPES, uploadAsset } from './assets'
  import MathPopover from './MathPopover.svelte'
  import { openMathEditor } from './mathEditor'
  import { ImageBlock, ImageUpload, MathNode, uploadAndInsert } from './media'
  import { PageBreak } from './pageBreak'
  import { loadQuota, type Quota } from '../session'
  import { TemplatedQuestion, questionNode } from './templatedQuestion'

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
  let quota: Quota | null = null
  let selectedId: string | null = null // the block the author is in (for the inspector)
  let previewHtml: string | null = null
  let tick = 0 // bumps on every editor transaction so toolbar state re-reads

  $: blocks = numberedNodes(content)
  $: marks = totalMarks(content)
  $: statusLabel = {
    saved: 'Saved',
    dirty: 'Unsaved changes',
    saving: 'Saving…',
    conflict: 'Conflict',
    error: 'Save failed — will retry',
  }[status]

  function scheduleSave() {
    if (!editor || !autosaver) return
    autosaver.schedule(buildDocument(title, editor.getJSON() as DocJSON))
  }

  onMount(async () => {
    void loadQuota().then((q) => (quota = q))
    try {
      const rec = await getDocument(id)
      title = rec.document.title
      content = rec.document.content
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
          FreeformQuestion.configure({ onAddBelow: (pos: number) => (pickerAt = pos) }),
          TemplatedQuestion.configure({
            onAddBelow: (pos: number) => (pickerAt = pos),
            onNotice: (m: string) => (notice = m),
          }),
        ],
        content: rec.document.content,
        onUpdate: ({ editor: e }) => {
          content = e.getJSON() as DocJSON
          scheduleSave()
        },
        onTransaction: () => (tick += 1),
      })
      content = editor.getJSON() as DocJSON
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
    void autosaver?.flush()
    unsubscribe?.()
    editor?.destroy()
  })

  function onBeforeUnload(e: BeforeUnloadEvent) {
    if (status === 'dirty' || status === 'saving' || status === 'error') e.preventDefault()
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
    editor.chain().focus().insertContentAt(insertionPoint(editor), questionNode(q)).run()
    pickerAt = undefined
  }

  function insertFreeformQuestion() {
    if (!editor) return
    insertFreeform(editor, insertionPoint(editor), freeformNode())
    pickerAt = undefined
  }

  // A free-form answer is edited in the key region and stored on its question's node.
  function setAnswer(blockId: string, answer: DocJSON) {
    if (!editor) return
    const { doc, tr } = editor.state
    let target: number | null = null
    doc.descendants((node, pos) => {
      if (target === null && node.type.name === 'freeformQuestion' && node.attrs.block_id === blockId)
        target = pos
      return false
    })
    if (target === null) return
    const node = doc.nodeAt(target)
    if (!node) return
    tr.setNodeMarkup(target, undefined, { ...node.attrs, answer })
    editor.view.dispatch(tr)
  }

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
  $: headingActive = [act.h1, act.h2, act.h3]

  async function download(mode: ExportMode) {
    busy = `export-${mode}`
    actionError = ''
    try {
      await autosaver?.flush()
      const blob = await exportDocument(id, mode)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${title || 'paper'}-${mode}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      actionError = e instanceof Error ? e.message : String(e)
    } finally {
      busy = ''
      void loadQuota().then((q) => (quota = q))
    }
  }

  async function preview(mode: ExportMode) {
    busy = 'preview'
    actionError = ''
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

<svelte:window on:beforeunload={onBeforeUnload} />

<div class="bar">
  <a class="back" href="#/">← Papers</a>
  <span class="chip {status}" role="status" aria-live="polite">{statusLabel}</span>
  <span class="total">{marks} marks</span>
  <span class="spacer"></span>
  {#if quota && typeof quota.left_day === 'number'}
    <span class="quota" title="PDF exports left in the last 24 hours">{quota.left_day} exports left today</span>
  {/if}
  <AccountChip />
  <div class="export" role="group" aria-label="Export">
    <button disabled={!!busy} on:click={() => preview('full')}>Preview</button>
    <button disabled={!!busy} on:click={() => download('student')}>Student PDF</button>
    <button disabled={!!busy || blocks.length === 0} on:click={() => download('key')}
      >Answer key PDF</button
    >
    <button disabled={!!busy} on:click={() => download('full')}>Full copy PDF</button>
  </div>
</div>

{#if status === 'conflict'}
  <p class="banner" role="alert">
    This paper changed in another tab or window. Your latest edits were not saved.
    <button on:click={() => location.reload()}>Reload</button>
  </p>
{/if}
{#if actionError}<p class="banner err" role="alert">{actionError}</p>{/if}
{#if notice}
  <p class="banner note" aria-live="polite">
    {notice} <button on:click={() => (notice = '')}>Dismiss</button>
  </p>
{/if}

{#if loading}
  <p class="loading">Loading…</p>
{:else if loadError}
  <p class="banner err" role="alert">{loadError} <a href="#/">Back to papers</a></p>
{/if}

<div class="desk" class:hidden={loading || !!loadError}>
<div class="main">
  <div class="tools" role="toolbar" aria-label="Formatting">
    <button
      aria-pressed={act.bold}
      on:click={() => editor?.chain().focus().toggleBold().run()}><b>B</b></button
    >
    <button
      aria-pressed={act.italic}
      on:click={() => editor?.chain().focus().toggleItalic().run()}><i>I</i></button
    >
    <button
      aria-pressed={act.underline}
      on:click={() => editor?.chain().focus().toggleUnderline().run()}><u>U</u></button
    >
    <span class="sep"></span>
    {#each [1, 2, 3] as level (level)}
      <button
        aria-pressed={headingActive[level - 1]}
        on:click={() => editor?.chain().focus().toggleHeading({ level: level as 1 | 2 | 3 }).run()}
        >H{level}</button
      >
    {/each}
    <span class="sep"></span>
    <button
      aria-pressed={act.bullet}
      on:click={() => editor?.chain().focus().toggleBulletList().run()}>• List</button
    >
    <button
      aria-pressed={act.ordered}
      on:click={() => editor?.chain().focus().toggleOrderedList().run()}>1. List</button
    >
    <button on:click={() => editor?.chain().focus().insertContent({ type: 'pageBreak' }).run()}
      >Page break</button
    >
    <span class="sep"></span>
    <button disabled={!act.inText} on:click={addEquation}>Equation</button>
    <button on:click={() => fileInput.click()}>Image</button>
    <input
      bind:this={fileInput}
      type="file"
      accept={IMAGE_TYPES.join(',')}
      multiple
      hidden
      aria-label="Choose image"
      on:change={onPickImages}
    />
    <span class="sep"></span>
    <button aria-label="Undo" on:click={() => editor?.chain().focus().undo().run()}>↶</button>
    <button aria-label="Redo" on:click={() => editor?.chain().focus().redo().run()}>↷</button>
  </div>

  <div class="page">
    <input
      class="title"
      aria-label="Paper title"
      placeholder="Untitled paper"
      bind:value={title}
      on:input={scheduleSave}
    />
    <p class="sheetmeta"><span>Name: ______________</span><span>Total: {marks} marks</span></p>
    <div
      class="surface"
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
    on:answer={(e) => setAnswer(e.detail.blockId, e.detail.answer)}
    on:error={(e) => (actionError = e.detail)}
  />
</div>
<Inspector {blocks} {marks} {selectedId} />
</div>

<MathPopover />

{#if pickerAt !== undefined}
  <AddQuestion
    on:insert={(e) => insertQuestion(e.detail.question)}
    on:freeform={insertFreeformQuestion}
    on:close={() => (pickerAt = undefined)}
  />
{/if}

{#if previewHtml !== null}
  <div class="backdrop" role="presentation" on:click|self={() => (previewHtml = null)}>
    <div class="preview" role="dialog" aria-modal="true" aria-label="Print preview">
      <button class="close" aria-label="Close preview" on:click={() => (previewHtml = null)}
        >×</button
      >
      <iframe title="Print preview" srcdoc={previewHtml}></iframe>
    </div>
  </div>
{/if}

<style>
  .bar {
    position: sticky;
    top: 0;
    z-index: 10;
    display: flex;
    align-items: center;
    gap: 0.8rem;
    padding: 0.5rem 1rem;
    background: var(--paper-2);
    border-bottom: 1px solid var(--line);
    font-size: 13px;
  }
  .back {
    color: var(--ink-soft);
    text-decoration: none;
  }
  .chip {
    font-family: var(--mono);
    font-size: 11.5px;
    padding: 0.1rem 0.5rem;
    border-radius: 999px;
    background: var(--verify-soft);
    color: var(--verify-ink);
  }
  .chip.dirty,
  .chip.saving {
    background: var(--paper-sink);
    color: var(--ink-soft);
  }
  .chip.conflict,
  .chip.error {
    background: var(--mark-soft);
    color: var(--mark);
  }
  .total {
    font-family: var(--mono);
    color: var(--mark);
  }
  .quota {
    color: var(--ink-faint);
    font-size: 12.5px;
  }
  .spacer {
    flex: 1;
  }
  .export {
    display: flex;
    gap: 0.35rem;
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
  button[aria-pressed='true'] {
    background: var(--verify-soft);
    border-color: var(--verify);
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
  .loading {
    text-align: center;
    color: var(--ink-faint);
  }
  .hidden {
    display: none;
  }

  .desk {
    display: flex;
    justify-content: center;
    gap: 1rem;
    background: var(--desk);
    padding: 1rem 1rem 4rem;
    min-height: 100vh;
  }
  .main {
    flex: 1 1 auto;
    min-width: 0;
  }
  @media (max-width: 1150px) {
    .desk {
      flex-direction: column;
    }
  }
  .tools {
    width: 210mm;
    max-width: 100%;
    margin: 0 auto 0.6rem;
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
    align-items: center;
  }
  .sep {
    width: 1px;
    height: 1.2rem;
    background: var(--line);
    margin: 0 0.2rem;
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
    counter-reset: q;
    font-family: var(--serif);
  }
  .surface :global(.qblock) {
    counter-increment: q;
  }
  .surface :global(.ffblock) {
    display: grid;
    grid-template-columns: 2rem 1fr;
    gap: 0.25rem;
    padding: 0.6rem 0.4rem;
    border: 1px solid transparent;
    border-radius: 8px;
  }
  .surface :global(.ffblock:hover),
  .surface :global(.ffblock:focus-within) {
    border-color: var(--line);
    background: var(--wash);
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
  .surface :global(.ff-bar) {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.3rem;
    margin-top: 0.4rem;
    opacity: 0;
    transition: opacity 0.12s;
    font-family: var(--sans);
    font-size: 12px;
  }
  .surface :global(.ffblock:hover .ff-bar),
  .surface :global(.ffblock:focus-within .ff-bar) {
    opacity: 1;
  }
  .surface :global(.ff-spacer) {
    flex: 1;
  }
  .surface :global(.ff-marks-input) {
    width: 3.6rem;
    font: inherit;
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 0.15rem 0.3rem;
    background: var(--paper);
    color: var(--ink);
  }
  .surface :global(.ff-bar button) {
    font: inherit;
    border: 1px solid var(--line);
    background: var(--paper);
    color: var(--ink);
    border-radius: 6px;
    padding: 0.2rem 0.55rem;
    cursor: pointer;
  }
  .surface :global(.ff-bar button.danger) {
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
  .preview iframe {
    width: 100%;
    height: 100%;
    border: none;
  }
  .close {
    position: absolute;
    right: 0.6rem;
    top: 0.4rem;
    z-index: 2;
    font-size: 1.2rem;
  }
</style>
