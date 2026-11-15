<script lang="ts">
  // Home: the teacher's papers. New / open / delete (delete asks twice, inline).
  import { onMount } from 'svelte'
  import {
    createDocument,
    deleteDocument,
    generatePaper,
    listDocuments,
    listPaperTemplates,
    type PaperTemplateInfo,
  } from './docsApi'
  import { lastReport } from './paperReport'
  import type { DocumentSummary } from './doc'
  import { navigate } from '../router'
  import AccountChip from './AccountChip.svelte'
  import { settings } from '../settings'

  let docs: DocumentSummary[] = []
  let loaded = false
  let error = ''
  let confirmId: string | null = null
  // Paper templates (P8a) come from the engine: the starter buttons and the generator.
  let templates: PaperTemplateInfo[] = []
  let levels: string[] = ['P5', 'P6']
  let genTemplate = ''
  let genLevel = 'P6'
  let generating = false

  const msg = (e: unknown): string => (e instanceof Error ? e.message : String(e))

  async function refresh() {
    try {
      docs = await listDocuments()
    } catch (e) {
      error = msg(e)
    } finally {
      loaded = true
    }
  }
  onMount(() => {
    void refresh()
    void loadTemplates()
  })

  async function loadTemplates() {
    try {
      const res = await listPaperTemplates()
      templates = res.templates
      levels = res.levels
      genTemplate = genTemplate || (templates[templates.length - 1]?.code ?? '')
    } catch (e) {
      error = msg(e)
    }
  }

  async function onGenerate() {
    if (!genTemplate || generating) return
    error = ''
    generating = true
    try {
      const rec = await generatePaper(genTemplate, genLevel)
      lastReport.set({ docId: rec.id, report: rec.report })
      navigate(`/docs/${rec.id}`)
    } catch (e) {
      error = msg(e)
    } finally {
      generating = false
    }
  }

  async function onNew() {
    error = ''
    try {
      const rec = await createDocument()
      navigate(`/docs/${rec.id}`)
    } catch (e) {
      error = msg(e)
    }
  }

  async function onTemplate(t: PaperTemplateInfo) {
    error = ''
    try {
      const rec = await createDocument(undefined, t.code)
      navigate(`/docs/${rec.id}`)
    } catch (e) {
      error = msg(e)
    }
  }

  async function onDelete(id: string) {
    if (confirmId !== id) {
      confirmId = id
      return
    }
    error = ''
    try {
      await deleteDocument(id)
      confirmId = null
      docs = docs.filter((d) => d.id !== id)
    } catch (e) {
      error = msg(e)
    }
  }

  const when = (iso: string): string => new Date(iso).toLocaleString()
</script>

<main>
  <div class="masthead">
    <span class="wordmark">exam-paper-synthesis</span>
    <nav class="links" aria-label="More">
      {#if $settings?.classic_generator}<a class="classic" href="#/classic">Classic generator</a>{/if}
      <a class="classic" href="#/settings">Settings</a>
    </nav>
    <AccountChip />
  </div>
  <div class="head">
    <h1>Your papers</h1>
    <button class="new" on:click={onNew}>+ New paper</button>
  </div>

  <div class="templates" role="group" aria-label="Start from a template">
    <span class="tlabel">Start from a template</span>
    {#each templates as t (t.code)}
      <button class="tpl" on:click={() => onTemplate(t)}>{t.label}</button>
    {/each}
  </div>

  <form class="generate" aria-label="Generate a paper" on:submit|preventDefault={onGenerate}>
    <span class="tlabel">Generate a whole paper</span>
    <label>
      Paper
      <select bind:value={genTemplate} aria-label="Paper to generate">
        {#each templates as t (t.code)}<option value={t.code}>{t.label}</option>{/each}
      </select>
    </label>
    <label>
      Level
      <select bind:value={genLevel} aria-label="Level">
        {#each levels as l (l)}<option value={l}>{l}</option>{/each}
      </select>
    </label>
    <button class="gen" type="submit" disabled={!genTemplate || generating}>
      {generating ? 'Generating…' : 'Generate paper'}
    </button>
  </form>

  {#if error}<p class="error" role="alert">{error}</p>{/if}

  {#if loaded && docs.length === 0 && !error}
    <p class="empty">No papers yet. Start with <b>New paper</b>.</p>
  {/if}

  <ul class="docs">
    {#each docs as d (d.id)}
      <li class="doc">
        <a class="open" href={`#/docs/${d.id}`}>
          <span class="t">{d.title || 'Untitled paper'}</span>
          <span class="m">{d.total_marks} marks · edited {when(d.updated_at)}</span>
        </a>
        <button class="del" on:click={() => onDelete(d.id)}>
          {confirmId === d.id ? 'Confirm delete' : 'Delete'}
        </button>
      </li>
    {/each}
  </ul>
</main>

<style>
  main {
    max-width: 760px;
    margin: 0 auto;
    padding: 2.5rem 1.35rem 4.5rem;
  }
  .masthead {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 1.5rem;
  }
  .wordmark {
    font-family: var(--mono);
    font-size: 13.5px;
    font-weight: 600;
  }
  .links {
    display: flex;
    gap: 1rem;
    margin-left: auto;
    margin-right: 1rem;
  }
  .classic {
    font-size: 12.5px;
    color: var(--ink-faint);
  }
  .head {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  h1 {
    font-family: var(--serif);
    margin: 0;
  }
  .new {
    font: inherit;
    border: 1px solid var(--verify);
    background: var(--verify);
    color: #fff;
    border-radius: 8px;
    padding: 0.5rem 1rem;
    cursor: pointer;
  }
  .templates {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.9rem;
  }
  .tlabel {
    font-size: 12.5px;
    color: var(--ink-faint);
  }
  .tpl {
    font: inherit;
    font-size: 13px;
    border: 1px solid var(--line);
    background: var(--paper-2);
    color: var(--ink);
    border-radius: 8px;
    padding: 0.35rem 0.8rem;
    cursor: pointer;
  }
  .generate {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem 0.8rem;
    margin: 0.6rem 0 0;
    font-size: 13px;
    color: var(--ink-soft);
  }
  .generate label {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
  }
  .generate select {
    font: inherit;
    font-size: 13px;
    border: 1px solid var(--line);
    border-radius: 6px;
    background: var(--paper);
    color: var(--ink);
    padding: 0.2rem 0.4rem;
  }
  .gen {
    font: inherit;
    font-size: 13px;
    border: 1px solid var(--verify);
    background: var(--verify-soft, var(--paper-2));
    color: var(--ink);
    border-radius: 8px;
    padding: 0.35rem 0.8rem;
    cursor: pointer;
  }
  .gen:disabled {
    opacity: 0.6;
    cursor: default;
  }
  .docs {
    list-style: none;
    padding: 0;
    margin: 1.2rem 0 0;
    display: grid;
    gap: 0.5rem;
  }
  .doc {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    border: 1px solid var(--line);
    background: var(--paper-2);
    border-radius: 10px;
    padding: 0.7rem 0.9rem;
  }
  .open {
    flex: 1;
    display: grid;
    text-decoration: none;
    color: inherit;
  }
  .t {
    font-family: var(--serif);
    font-size: 1.1rem;
  }
  .m {
    font-size: 12px;
    color: var(--ink-faint);
    font-family: var(--mono);
  }
  .del {
    font: inherit;
    font-size: 12px;
    border: 1px solid var(--line);
    background: var(--paper);
    border-radius: 6px;
    padding: 0.25rem 0.6rem;
    color: var(--mark);
    cursor: pointer;
  }
  .empty {
    color: var(--ink-soft);
  }
  .error {
    color: var(--mark);
  }
</style>
