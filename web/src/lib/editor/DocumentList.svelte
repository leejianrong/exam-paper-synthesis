<script lang="ts">
  // Home: the teacher's papers. New / open / delete (delete asks twice, inline).
  import { onMount } from 'svelte'
  import { createDocument, deleteDocument, listDocuments } from './docsApi'
  import type { DocumentSummary } from './doc'
  import { navigate } from '../router'

  let docs: DocumentSummary[] = []
  let loaded = false
  let error = ''
  let confirmId: string | null = null

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
  onMount(refresh)

  async function onNew() {
    error = ''
    try {
      const rec = await createDocument()
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
    <a class="classic" href="#/classic">Classic generator</a>
  </div>
  <div class="head">
    <h1>Your papers</h1>
    <button class="new" on:click={onNew}>+ New paper</button>
  </div>

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
