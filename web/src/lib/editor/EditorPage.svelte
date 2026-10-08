<script lang="ts">
  // The WYSIWYG page (W1c): an A4-width column of rich text and question blocks, a "+"
  // to add questions, the answer key below, autosave, and the export/preview menu.
  import { onDestroy, onMount } from 'svelte'
  import { Editor } from '@tiptap/core'
  import StarterKit from '@tiptap/starter-kit'
  import type { Question } from '../types'
  import AddQuestion from './AddQuestion.svelte'
  import AnswerKey from './AnswerKey.svelte'
  import { createAutosaver, type Autosaver } from './autosave'
  import { buildDocument, questionsOf, totalMarks, type DocJSON } from './doc'
  import {
    ApiError,
    exportDocument,
    getDocument,
    previewDocument,
    saveDocument,
    type ExportMode,
  } from './docsApi'
  import { PageBreak } from './pageBreak'
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
  let previewHtml: string | null = null
  let tick = 0 // bumps on every editor transaction so toolbar state re-reads

  $: questions = questionsOf(content) as Question[]
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
            heading: { levels: [1, 2, 3] },
            // Only the node/mark types the document schema allows (document.schema.json).
            blockquote: false,
            code: false,
            codeBlock: false,
            horizontalRule: false,
            strike: false,
            link: false,
          }),
          PageBreak,
          TemplatedQuestion.configure({ onAddBelow: (pos: number) => (pickerAt = pos) }),
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

  function insertQuestion(q: Question) {
    if (!editor) return
    const { doc } = editor.state
    // "Add question" at the end goes before the editor's empty trailing paragraph, so
    // repeated inserts stack with no blank gap between them.
    const last = doc.lastChild
    const trailing = last?.type.name === 'paragraph' && last.content.size === 0
    const at = pickerAt ?? (trailing && last ? doc.content.size - last.nodeSize : doc.content.size)
    editor.chain().focus().insertContentAt(at, questionNode(q)).run()
    pickerAt = undefined
  }

  // Toolbar state, re-read after every editor transaction (`tick`).
  function readActive(revision: number) {
    const e = editor
    return {
      revision,
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
  <div class="export" role="group" aria-label="Export">
    <button disabled={!!busy} on:click={() => preview('full')}>Preview</button>
    <button disabled={!!busy} on:click={() => download('student')}>Student PDF</button>
    <button disabled={!!busy || questions.length === 0} on:click={() => download('key')}
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

{#if loading}
  <p class="loading">Loading…</p>
{:else if loadError}
  <p class="banner err" role="alert">{loadError} <a href="#/">Back to papers</a></p>
{/if}

<div class="desk" class:hidden={loading || !!loadError}>
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
    <div class="surface" bind:this={element}></div>

    <button class="plus" aria-label="Add question" on:click={() => (pickerAt = null)}>
      <span class="plus-sign">+</span> Add question
    </button>
  </div>

  <AnswerKey {questions} />
</div>

{#if pickerAt !== undefined}
  <AddQuestion
    on:insert={(e) => insertQuestion(e.detail.question)}
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
  .loading {
    text-align: center;
    color: var(--ink-faint);
  }
  .hidden {
    display: none;
  }

  .desk {
    background: var(--desk);
    padding: 1rem 1rem 4rem;
    min-height: 100vh;
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
