<script lang="ts">
  // The equation editor (W2b): a LaTeX field with a live KaTeX preview and one-click
  // snippets for the forms P5–P6 papers use. Mounted once by the page; any math node, in
  // the page or in an answer, opens it through `mathRequest`.
  import { tick } from 'svelte'
  import { closeMathEditor, mathRequest } from './mathEditor'
  import { MATH_SNIPPETS, mountMath } from './math'

  const MAX = 500

  let latex = ''
  let error = ''
  let field: HTMLTextAreaElement | undefined
  let preview: HTMLSpanElement | undefined
  let seq = 0

  $: request = $mathRequest
  // A new request resets the field (the store is the only writer).
  $: if (request) {
    latex = request.latex
    void tick().then(() => field?.focus())
  }

  $: delimiterError = /\\[()[\]]/.test(latex) ? 'Leave out \\( \\) \\[ \\] — the formula is wrapped for you.' : ''
  $: if (request && preview) void render(latex)

  async function render(source: string) {
    const mine = ++seq
    if (!preview) return
    if (source.trim() === '') {
      preview.shadowRoot?.replaceChildren()
      error = ''
      return
    }
    const res = await mountMath(preview, source)
    if (mine === seq) error = res.ok ? '' : (res.error ?? 'Cannot typeset this formula')
  }

  function insertSnippet(snippet: string) {
    if (!field) return
    const start = field.selectionStart ?? latex.length
    const end = field.selectionEnd ?? latex.length
    latex = latex.slice(0, start) + snippet + latex.slice(end)
    void tick().then(() => {
      field?.focus()
      field?.setSelectionRange(start + snippet.length, start + snippet.length)
    })
  }

  $: canApply = latex.trim() !== '' && latex.length <= MAX && !delimiterError && !error

  function apply() {
    if (!request || !canApply) return
    request.apply(latex.trim())
    closeMathEditor()
  }

  function remove() {
    request?.apply(null)
    closeMathEditor()
  }

  function onKey(e: KeyboardEvent) {
    if (!request) return
    if (e.key === 'Escape') closeMathEditor()
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) apply()
  }
</script>

<svelte:window on:keydown={onKey} />

{#if request}
  <div class="backdrop" role="presentation" on:click|self={closeMathEditor}>
    <div class="dialog" role="dialog" aria-modal="true" aria-label="Equation">
      <header>
        <h2>Equation</h2>
        <button class="x" aria-label="Close" on:click={closeMathEditor}>×</button>
      </header>
      <div class="snippets" role="group" aria-label="Insert">
        {#each MATH_SNIPPETS as s (s.label)}
          <button type="button" on:click={() => insertSnippet(s.latex)}>{s.label}</button>
        {/each}
      </div>
      <label class="field"
        ><span>LaTeX</span>
        <textarea
          bind:this={field}
          bind:value={latex}
          rows="3"
          maxlength={MAX}
          spellcheck="false"
          aria-label="LaTeX"
        ></textarea>
      </label>
      <div class="preview" aria-label="Preview">
        <span class="label">Preview</span>
        <span class="math-host" bind:this={preview}></span>
      </div>
      {#if delimiterError}<p class="error" role="alert">{delimiterError}</p>
      {:else if error}<p class="error" role="alert">Cannot typeset this: {error}</p>{/if}
      <footer>
        <button class="danger" on:click={remove}>Remove</button>
        <span class="spacer"></span>
        <button on:click={closeMathEditor}>Cancel</button>
        <button class="primary" disabled={!canApply} on:click={apply}>Apply</button>
      </footer>
    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba(25, 28, 33, 0.5);
    display: grid;
    place-items: center;
    z-index: 70;
  }
  .dialog {
    width: min(520px, 94vw);
    background: var(--page);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    box-shadow: var(--shadow);
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  h2 {
    margin: 0;
    font-family: var(--serif);
    font-size: 1.1rem;
  }
  .snippets {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
    margin: 0.6rem 0;
  }
  button {
    font: inherit;
    font-size: 12.5px;
    border: 1px solid var(--line);
    background: var(--paper);
    color: var(--ink);
    border-radius: 6px;
    padding: 0.25rem 0.6rem;
    cursor: pointer;
  }
  button:disabled {
    opacity: 0.5;
    cursor: default;
  }
  .primary {
    background: var(--verify-soft);
    border-color: var(--verify);
  }
  .danger {
    color: var(--mark);
  }
  .x {
    border: none;
    background: none;
    font-size: 1.2rem;
  }
  .field {
    display: block;
  }
  .field span,
  .label {
    display: block;
    font-size: 11.5px;
    color: var(--ink-faint);
    margin-bottom: 0.15rem;
  }
  textarea {
    width: 100%;
    box-sizing: border-box;
    font-family: var(--mono);
    font-size: 13px;
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 0.4rem 0.5rem;
    background: var(--paper);
    color: var(--ink);
    resize: vertical;
  }
  .preview {
    margin: 0.7rem 0 0.3rem;
    min-height: 3rem;
    padding: 0.5rem 0.7rem;
    border: 1px dashed var(--line);
    border-radius: 6px;
    font-size: 1.15rem;
  }
  .math-host {
    display: inline-block;
    font-size: inherit;
    font-family: inherit;
    color: inherit;
  }
  .error {
    color: var(--mark);
    font-size: 12.5px;
    margin: 0.3rem 0 0;
  }
  footer {
    display: flex;
    gap: 0.4rem;
    margin-top: 0.8rem;
  }
  .spacer {
    flex: 1;
  }
</style>
