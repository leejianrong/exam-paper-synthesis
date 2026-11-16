<script lang="ts">
  // Home: the teacher's papers, grouped by folder (O2), then Unfiled. New / open / delete
  // (delete asks twice, inline); folders are created, renamed and deleted here, and a paper's
  // Move menu files it in a folder or back in Unfiled.
  import { onMount, tick } from 'svelte'
  import {
    createDocument,
    createFolder,
    deleteDocument,
    deleteFolder,
    generatePaper,
    listDocuments,
    listFolders,
    listPaperTemplates,
    moveDocument,
    renameFolder,
    type Folder,
    type PaperTemplateInfo,
  } from './docsApi'
  import { groupByFolder } from './folders'
  import FolderSection from './FolderSection.svelte'
  import MoveMenu from './MoveMenu.svelte'
  import { lastReport } from './paperReport'
  import type { DocumentSummary } from './doc'
  import { navigate } from '../router'
  import AccountChip from './AccountChip.svelte'
  import { settings } from '../settings'

  let docs: DocumentSummary[] = []
  let folders: Folder[] = []
  let loaded = false
  // The inline "New folder" field, and a polite announcement of what a folder action did.
  let creatingFolder = false
  let newFolderName = ''
  let newFolderInput: HTMLInputElement
  let newFolderButton: HTMLButtonElement
  let announce = ''
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
      ;[docs, folders] = await Promise.all([listDocuments(), listFolders()])
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

  async function openNewFolder() {
    creatingFolder = true
    newFolderName = ''
    await tick()
    newFolderInput?.focus()
  }

  async function closeNewFolder() {
    creatingFolder = false
    await tick()
    newFolderButton?.focus()
  }

  async function onCreateFolder() {
    const name = newFolderName.trim()
    if (!name) return
    error = ''
    try {
      const f = await createFolder(name)
      // Keep the API's order (by name, case-insensitive) without a reload.
      folders = [...folders, f].sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: 'base' }))
      announce = `Folder “${f.name}” created.`
      await closeNewFolder()
    } catch (e) {
      error = msg(e)
    }
  }

  async function onRenameFolder(id: string, name: string): Promise<boolean> {
    error = ''
    try {
      const f = await renameFolder(id, name)
      folders = folders
        .map((x) => (x.id === id ? f : x))
        .sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: 'base' }))
      announce = `Folder renamed to “${f.name}”.`
      return true
    } catch (e) {
      error = msg(e)
      return false
    }
  }

  async function onDeleteFolder(id: string) {
    error = ''
    try {
      await deleteFolder(id)
      const name = folders.find((f) => f.id === id)?.name ?? ''
      folders = folders.filter((f) => f.id !== id)
      docs = docs.map((d) => (d.folder_id === id ? { ...d, folder_id: null } : d))
      announce = `Folder “${name}” deleted. Its papers are in Unfiled.`
    } catch (e) {
      error = msg(e)
    }
  }

  async function onMove(d: DocumentSummary, folderId: string | null) {
    error = ''
    try {
      const rec = await moveDocument(d.id, folderId)
      docs = docs.map((x) => (x.id === d.id ? { ...x, folder_id: rec.folder_id ?? null } : x))
      const where = folders.find((f) => f.id === folderId)?.name
      announce = `Moved “${d.title || 'Untitled paper'}” to ${where ? `“${where}”` : 'Unfiled'}.`
    } catch (e) {
      error = msg(e)
    }
  }

  $: grouped = groupByFolder(folders, docs)

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

  {#snippet row(d: DocumentSummary)}
    <li class="doc">
      <a class="open" href={`#/docs/${d.id}`}>
        <span class="t">{d.title || 'Untitled paper'}</span>
        <span class="m">{d.total_marks} marks · edited {when(d.updated_at)}</span>
      </a>
      <div class="rowacts">
        {#if folders.length > 0}
          <MoveMenu
            title={d.title || 'Untitled paper'}
            {folders}
            current={folders.some((f) => f.id === d.folder_id) ? (d.folder_id ?? null) : null}
            onMove={(id) => onMove(d, id)}
          />
        {/if}
        <button class="del" on:click={() => onDelete(d.id)}>
          {confirmId === d.id ? 'Confirm delete' : 'Delete'}
        </button>
      </div>
    </li>
  {/snippet}

  <div class="listbar">
    {#if creatingFolder}
      <form class="newfolder" aria-label="New folder" on:submit|preventDefault={onCreateFolder}>
        <input
          bind:this={newFolderInput}
          bind:value={newFolderName}
          aria-label="Folder name"
          placeholder="e.g. 2026 Prelims"
          maxlength="80"
          required
          on:keydown={(e) => e.key === 'Escape' && closeNewFolder()}
        />
        <button class="tpl primary" type="submit" disabled={!newFolderName.trim()}>Create folder</button>
        <button class="tpl" type="button" on:click={closeNewFolder}>Cancel</button>
      </form>
    {:else}
      <button class="tpl" bind:this={newFolderButton} on:click={openNewFolder}>+ New folder</button>
    {/if}
  </div>
  <p class="sr" role="status">{announce}</p>

  {#if !loaded}
    <p class="empty">Loading your papers…</p>
  {:else if docs.length === 0 && folders.length === 0 && !error}
    <p class="empty">No papers yet. Start with <b>New paper</b>.</p>
  {:else}
    {#if grouped.groups.length > 0}
      <div class="folders">
        {#each grouped.groups as g (g.folder.id)}
          <FolderSection
            group={g}
            onRename={(name) => onRenameFolder(g.folder.id, name)}
            onDelete={() => onDeleteFolder(g.folder.id)}
          >
            <ul class="docs" aria-label={`Papers in “${g.folder.name}”`}>
              {#each g.docs as d (d.id)}{@render row(d)}{/each}
            </ul>
          </FolderSection>
        {/each}
      </div>
    {/if}

    <section class="unfiled" aria-labelledby={folders.length > 0 ? 'unfiled-h' : undefined}>
      {#if folders.length > 0}
        <h2 id="unfiled-h">Unfiled</h2>
        {#if grouped.unfiled.length === 0}
          <p class="empty">Every paper is in a folder.</p>
        {/if}
      {/if}
      {#if grouped.unfiled.length > 0}
        <ul class="docs" aria-label={folders.length > 0 ? 'Unfiled papers' : 'Papers'}>
          {#each grouped.unfiled as d (d.id)}{@render row(d)}{/each}
        </ul>
      {/if}
    </section>
  {/if}
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
  .listbar {
    margin-top: 1.4rem;
    min-height: 32px;
    display: flex;
    align-items: center;
  }
  .newfolder {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.4rem;
  }
  .newfolder input {
    font: inherit;
    font-size: 13px;
    width: 16rem;
    max-width: 100%;
    border: 1px solid var(--line);
    border-radius: 6px;
    background: var(--paper);
    color: var(--ink);
    padding: 0.35rem 0.5rem;
  }
  .tpl.primary {
    border-color: var(--verify);
    background: var(--verify);
    color: #fff;
  }
  .tpl:disabled {
    opacity: 0.6;
    cursor: default;
  }
  .tpl:focus-visible,
  .newfolder input:focus-visible {
    outline: 2px solid var(--verify);
    outline-offset: 2px;
  }
  .rowacts {
    display: flex;
    gap: 0.5rem;
    margin-left: auto;
  }
  .folders {
    display: grid;
    gap: 0.8rem;
    margin-top: 0.9rem;
  }
  .folders .docs {
    margin: 0;
  }
  .unfiled h2 {
    font-family: var(--serif);
    font-size: 1.05rem;
    font-weight: 600;
    margin: 1.4rem 0 0;
  }
  .unfiled .empty {
    margin: 0.5rem 0 0;
    font-size: 13px;
  }
  .sr {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
  }
  .gen:disabled {
    opacity: 0.6;
    cursor: default;
  }
  .docs {
    list-style: none;
    padding: 0;
    margin: 0.6rem 0 0;
    display: grid;
    gap: 0.5rem;
  }
  .doc {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.6rem;
    border: 1px solid var(--line);
    background: var(--paper-2);
    border-radius: 10px;
    padding: 0.7rem 0.9rem;
  }
  .open {
    flex: 1 1 14rem;
    min-width: 0;
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
