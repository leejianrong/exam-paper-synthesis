<script lang="ts">
  // The editable answer for one free-form question, in the answer-key region. A compact
  // TipTap instance restricted to the answer schema (paragraphs, lists, bold/italic/
  // underline). Created lazily — on first sight or focus — so a 200-question paper does
  // not spin up 200 editors; until then it shows the saved answer as plain markup.
  import { createEventDispatcher, onDestroy, onMount } from 'svelte'
  import { Editor } from '@tiptap/core'
  import StarterKit from '@tiptap/starter-kit'
  import { Node } from '@tiptap/core'
  import { IMAGE_TYPES, uploadAsset } from './assets'
  import { blocksToHtml, normalizeAnswer, type DocJSON } from './doc'
  import { ImageBlock, ImageUpload, MathNode, uploadAndInsert } from './media'
  import { openMathEditor } from './mathEditor'
  import { typesetMath } from './math'

  export let value: DocJSON
  export let label = 'Answer'

  const dispatch = createEventDispatcher<{ change: { answer: DocJSON }; error: string }>()

  // An answer holds paragraphs, lists and images (no headings, no free-form blocks).
  const AnswerDocument = Node.create({ name: 'doc', topNode: true, content: '(block | media)+' })

  let host: HTMLDivElement
  let editor: Editor | null = null
  let observer: IntersectionObserver | null = null

  const same = (a: DocJSON, b: DocJSON) => JSON.stringify(a) === JSON.stringify(b)

  function create(focus = false) {
    if (editor || !host) return
    observer?.disconnect()
    editor = new Editor({
      element: host,
      extensions: [
        AnswerDocument,
        ImageBlock,
        MathNode,
        ImageUpload.configure({
          upload: (f: File) => uploadAsset(f, f.name),
          onError: (m: string) => dispatch('error', m),
        }),
        StarterKit.configure({
          document: false,
          heading: false,
          blockquote: false,
          code: false,
          codeBlock: false,
          horizontalRule: false,
          strike: false,
          link: false,
          // The main editor owns history (the answer is a transaction on its node).
          undoRedo: false,
        }),
      ],
      content: value,
      editorProps: { attributes: { 'aria-label': label, role: 'textbox' } },
      onUpdate: ({ editor: e }) => {
        const answer = normalizeAnswer(e.getJSON() as DocJSON)
        if (!same(answer, normalizeAnswer(value))) dispatch('change', { answer })
      },
    })
    if (focus) editor.commands.focus('end')
  }

  // A change that did not come from typing here (undo, another tab's reload) is pushed in.
  $: if (editor && !same(normalizeAnswer(editor.getJSON() as DocJSON), normalizeAnswer(value))) {
    editor.commands.setContent(value, { emitUpdate: false })
  }

  let fileInput: HTMLInputElement | undefined

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

  async function onPick() {
    const files = Array.from(fileInput?.files ?? [])
    if (fileInput) fileInput.value = ''
    if (editor)
      await uploadAndInsert(editor, files, {
        upload: (f) => uploadAsset(f, f.name),
        onError: (m) => dispatch('error', m),
      })
  }

  onMount(() => {
    if (typeof IntersectionObserver === 'undefined') {
      create()
      return
    }
    observer = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) create()
    })
    observer.observe(host)
  })

  onDestroy(() => {
    observer?.disconnect()
    editor?.destroy()
  })
</script>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<div class="answer" on:click={() => create(true)}>
  {#if editor}
    <div class="atools" role="toolbar" aria-label="Answer tools">
      <button type="button" on:click={addEquation}>Equation</button>
      <button type="button" on:click={() => fileInput?.click()}>Image</button>
      <input
        bind:this={fileInput}
        type="file"
        accept={IMAGE_TYPES.join(',')}
        multiple
        hidden
        aria-label="Choose answer image"
        on:change={onPick}
      />
    </div>
  {/if}
  {#if !editor}
    <div class="static" use:typesetMath={blocksToHtml(value?.content)}>
      {#if (value?.content ?? []).length}
        <!-- eslint-disable-next-line svelte/no-at-html-tags -- escaped by blocksToHtml -->
        {@html blocksToHtml(value.content)}
      {:else}
        <p class="ph">Write the answer…</p>
      {/if}
    </div>
  {/if}
  <div bind:this={host}></div>
</div>

<style>
  .answer {
    min-height: 2.4rem;
    border: 1px solid var(--line);
    border-radius: 6px;
    background: var(--page);
    padding: 0.35rem 0.6rem;
    cursor: text;
    font-family: var(--serif);
  }
  .answer:focus-within {
    border-color: var(--verify);
  }
  .answer :global(.ProseMirror) {
    outline: none;
    min-height: 1.6rem;
  }
  .answer :global(p) {
    margin: 0.2rem 0;
  }
  .atools {
    display: flex;
    gap: 0.3rem;
    margin-bottom: 0.3rem;
  }
  .atools button {
    font: inherit;
    font-family: var(--sans);
    font-size: 11.5px;
    border: 1px solid var(--line);
    background: var(--paper);
    color: var(--ink);
    border-radius: 6px;
    padding: 0.1rem 0.5rem;
    cursor: pointer;
  }
  .static :global(img),
  .answer :global(img) {
    max-width: 100%;
    height: auto;
  }
  :global(.math-host) {
    display: inline-block;
    font-size: inherit;
    font-family: inherit;
  }
  .ph {
    color: var(--ink-faint);
    margin: 0.2rem 0;
  }
</style>
