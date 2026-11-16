<script lang="ts">
  // Home: the teacher's papers, grouped by folder (O2), then Unfiled. "+ New" opens the wizard
  // (O3: folder, exam set, single paper, template, blank), as does a folder's "+ New in folder"
  // with that folder as the default home. Open / delete (asks twice, inline); folders are
  // renamed and deleted here, and a paper's Move menu files it in a folder or back in Unfiled.
  import { onMount, tick } from 'svelte'
  import {
    deleteDocument,
    deleteFolder,
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
  import NewWizard from './NewWizard.svelte'
  import type { DocumentSummary } from './doc'
  import AccountChip from './AccountChip.svelte'
  import { settings } from '../settings'

  let docs: DocumentSummary[] = []
  let folders: Folder[] = []
  let loaded = false
  // A polite announcement of what a folder action did.
  let announce = ''
  let error = ''
  let confirmId: string | null = null
  // Paper templates (P8a) come from the engine, for the wizard.
  let templates: PaperTemplateInfo[] = []
  let levels: string[] = ['P5', 'P6']
  // The + New wizard (O3): open or not, the folder it was opened from, and the button that
  // opened it (focus goes back there when it closes).
  let wizardOpen = false
  let wizardFolder: Folder | null = null
  let opener: HTMLElement | null = null

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
    } catch (e) {
      error = msg(e)
    }
  }

  function openWizard(e: Event, folder: Folder | null = null) {
    opener = e.currentTarget as HTMLElement
    wizardFolder = folder
    error = ''
    wizardOpen = true
  }

  async function closeWizard() {
    wizardOpen = false
    await tick()
    opener?.focus()
  }

  const byName = (a: Folder, b: Folder) => a.name.localeCompare(b.name, undefined, { sensitivity: 'base' })

  function onWizardFolder(f: Folder) {
    // Keep the API's order (by name, case-insensitive) without a reload.
    folders = [...folders, f].sort(byName)
    announce = `Folder “${f.name}” created.`
  }

  function onWizardPapers(made: DocumentSummary[]) {
    docs = [...made, ...docs.filter((d) => !made.some((m) => m.id === d.id))]
  }

  /** After the wizard made a folder or an exam set: close it and bring the folder into view. */
  async function showFolder(id: string) {
    wizardOpen = false
    await tick()
    const heading = document.getElementById(`folder-${id}`)
    if (!heading) return opener?.focus()
    heading.scrollIntoView?.({ block: 'start' })
    heading.focus()
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

  async function onRenameFolder(id: string, name: string): Promise<boolean> {
    error = ''
    try {
      const f = await renameFolder(id, name)
      folders = folders
        .map((x) => (x.id === id ? f : x))
        .sort(byName)
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
    <button class="new" aria-haspopup="dialog" on:click={(e) => openWizard(e)}>+ New</button>
  </div>

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

  <p class="sr" role="status">{announce}</p>

  {#if !loaded}
    <p class="empty">Loading your papers…</p>
  {:else if docs.length === 0 && folders.length === 0 && !error}
    <p class="empty">No papers yet. Start with <b>+ New</b>.</p>
  {:else}
    {#if grouped.groups.length > 0}
      <div class="folders">
        {#each grouped.groups as g (g.folder.id)}
          <FolderSection
            group={g}
            onRename={(name) => onRenameFolder(g.folder.id, name)}
            onDelete={() => onDeleteFolder(g.folder.id)}
            onNew={(e) => openWizard(e, g.folder)}
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

{#if wizardOpen}
  <NewWizard
    {folders}
    {templates}
    {levels}
    contextFolder={wizardFolder}
    onClose={closeWizard}
    onFolderCreated={onWizardFolder}
    onPapersCreated={onWizardPapers}
    onShowFolder={showFolder}
  />
{/if}

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
  .rowacts {
    display: flex;
    gap: 0.5rem;
    margin-left: auto;
  }
  .folders {
    display: grid;
    gap: 0.8rem;
    margin-top: 1.4rem;
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
