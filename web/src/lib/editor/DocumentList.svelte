<script lang="ts">
  // Home: the teacher's papers, grouped by folder (O2), then Unfiled. "+ New" opens the wizard
  // (O3: exam set, single paper, blank, folder), as does a folder's "New paper in folder…" with
  // that folder as the default home. EXA-166: each paper's actions (Open, Rename, Move, Make a
  // copy, Delete) and each folder's (New paper, Rename, Delete) sit behind a ⋯ menu; deleting
  // asks in a dialog. A search box filters papers by title, folders collapse (remembered per
  // viewer in localStorage), and edit times read en-SG, relative when recent. EXA-168: a folder
  // holding a complete exam set downloads one answer key for the set from its ⋯ menu.
  import { onMount, tick, untrack } from 'svelte'
  import {
    copyDocument,
    deleteDocument,
    deleteFolder,
    exportSetKey,
    listDocuments,
    listFolders,
    listPaperTemplates,
    moveDocument,
    renameDocument,
    renameFolder,
    setKeyUnfilled,
    type Folder,
    type PaperTemplateInfo,
  } from './docsApi'
  import { groupByFolder, setKeyStatus, titleMatches } from './folders'
  import FolderSection from './FolderSection.svelte'
  import PaperRow from './PaperRow.svelte'
  import MoveDialog from './MoveDialog.svelte'
  import NewWizard from './NewWizard.svelte'
  import ConfirmDialog from '../ConfirmDialog.svelte'
  import Icon from '../Icon.svelte'
  import type { DocumentRecord, DocumentSummary } from './doc'
  import AccountMenu from './AccountMenu.svelte'
  import { settings } from '../settings'
  import ErrorNote from '../ErrorNote.svelte'
  import { canRetry, createFailedText, errorText } from '../errors'

  const COLLAPSED_KEY = 'exam.papers.collapsed'

  let docs: DocumentSummary[] = $state([])
  let folders: Folder[] = $state([])
  let loaded = $state(false)
  // A polite announcement of what an action did.
  let announce = $state('')
  let error = $state('')
  /** Try again for the failure in `error`, when the same request may work now (EXA-165). */
  let errorRetry: (() => void) | null = $state(null)
  let errorRetryLabel: string | undefined = $state(undefined)
  /** EXA-168: the folder whose set key is being made, if any. */
  let setKeyFolder: string | null = $state(null)
  /** Why the list itself didn't load: it shows in place of the list, with Try again. */
  let listError: unknown = $state(null)
  // Paper templates (P8a) come from the engine, for the wizard.
  let templates: PaperTemplateInfo[] = $state([])
  let levels: string[] = $state(['P5', 'P6'])
  // The + New wizard (O3): open or not, the folder it was opened from, and the control that
  // opened it (focus goes back there when it closes).
  let wizardOpen = $state(false)
  let wizardFolder: Folder | null = $state(null)
  let opener: HTMLElement | null = null
  let query = $state('')
  let collapsed = $state(readCollapsed())
  let now = $state(new Date())
  let heading: HTMLElement | undefined = $state()
  let searchBox: HTMLInputElement | undefined = $state()
  // The open dialog, if any: move a paper, delete a paper, delete a folder.
  let moving: DocumentSummary | null = $state(null)
  let deleting: DocumentSummary | null = $state(null)
  let deletingFolder: Folder | null = $state(null)
  let dialogBusy = $state(false)
  let dialogError = $state('')

  /** Show a failed action in plain words, with Try again when it may work now. */
  function failed(e: unknown, action: string, retry?: () => void) {
    error = errorText(e, action)
    errorRetry = retry && canRetry(e) ? retry : null
    errorRetryLabel = undefined
  }
  function clearError() {
    error = ''
    errorRetry = null
    errorRetryLabel = undefined
  }
  const titleOf = (d: { title: string }): string => d.title || 'Untitled paper'

  function readCollapsed(): Set<string> {
    try {
      const ids: unknown = JSON.parse(localStorage.getItem(COLLAPSED_KEY) ?? '[]')
      return new Set(Array.isArray(ids) ? ids.filter((x): x is string => typeof x === 'string') : [])
    } catch {
      return new Set()
    }
  }

  function setCollapsed(next: Set<string>) {
    collapsed = next
    try {
      localStorage.setItem(COLLAPSED_KEY, JSON.stringify([...next]))
    } catch {
      // no storage (a private window, blocked site data): the choice lasts for this visit
    }
  }

  function toggleFolder(id: string) {
    setCollapsed(new Set(collapsed.has(id) ? [...collapsed].filter((x) => x !== id) : [...collapsed, id]))
  }

  async function refresh() {
    loaded = false
    listError = null
    try {
      ;[docs, folders] = await Promise.all([listDocuments(), listFolders()])
    } catch (e) {
      listError = e
    } finally {
      loaded = true
    }
  }

  onMount(() => {
    void refresh()
    void loadTemplates()
    // relative times ("5 min ago") move on while the page is open
    const clock = setInterval(() => (now = new Date()), 60_000)
    return () => clearInterval(clock)
  })

  async function loadTemplates() {
    try {
      const res = await listPaperTemplates()
      templates = res.templates
      levels = res.levels
      if (errorRetry === retryTemplates) clearError()
    } catch (e) {
      failed(e, "Couldn't load the paper templates", retryTemplates)
    }
  }

  const retryTemplates = () => void loadTemplates()

  function openWizard(from: HTMLElement | null, folder: Folder | null = null) {
    opener = from
    wizardFolder = folder
    clearError()
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

  /** After the wizard made a folder or an exam set: close it, open the folder and show it. */
  async function showFolder(id: string) {
    wizardOpen = false
    query = ''
    if (collapsed.has(id)) toggleFolder(id)
    await tick()
    const h = document.getElementById(`folder-${id}`)
    if (!h) return opener?.focus()
    h.scrollIntoView?.({ block: 'start' })
    ;(h.querySelector('button') ?? h).focus()
  }

  const summaryOf = (r: DocumentRecord, was: DocumentSummary): DocumentSummary => ({
    ...was,
    id: r.id,
    title: r.title,
    total_marks: r.total_marks,
    version: r.version,
    created_at: r.created_at,
    updated_at: r.updated_at,
    folder_id: r.folder_id ?? was.folder_id ?? null,
  })

  async function onRenamePaper(d: DocumentSummary, title: string): Promise<boolean> {
    clearError()
    try {
      const rec = await renameDocument(d.id, title)
      docs = docs.map((x) => (x.id === d.id ? summaryOf(rec, x) : x))
      announce = `Renamed to “${rec.title}”.`
      if (!titleMatches(rec.title, query)) {
        // the row has left the search results: its ⋯ is gone, so focus goes to the search box
        announce += ' It no longer matches the search.'
        await tick()
        searchBox?.focus()
      }
      return true
    } catch (e) {
      failed(e, "The paper wasn't renamed")
      return false
    }
  }

  async function onCopy(d: DocumentSummary) {
    clearError()
    try {
      const rec = await copyDocument(d.id)
      const copy = summaryOf(rec, { ...d, folder_id: d.folder_id ?? null })
      const at = docs.findIndex((x) => x.id === d.id)
      docs = [...docs.slice(0, at + 1), copy, ...docs.slice(at + 1)]
      announce = `Made “${titleOf(copy)}”.`
    } catch (e) {
      // no Try again: the copy may have been made although the reply was lost
      error = createFailedText(e, "Couldn't make a copy")
    }
  }

  function startDialog() {
    dialogBusy = false
    dialogError = ''
  }

  async function onMove(folderId: string | null) {
    const d = moving
    if (!d) return
    dialogBusy = true
    dialogError = ''
    try {
      const rec = await moveDocument(d.id, folderId)
      docs = docs.map((x) => (x.id === d.id ? { ...x, folder_id: rec.folder_id ?? null } : x))
      const where = folders.find((f) => f.id === folderId)?.name
      announce = `Moved “${titleOf(d)}” to ${where ? `“${where}”` : 'Unfiled'}.`
      if (folderId && collapsed.has(folderId)) toggleFolder(folderId)
      moving = null
      // the row moved to another group, so its ⋯ button is a new one: focus that
      await tick()
      document.querySelector<HTMLElement>(`[data-doc-id="${d.id}"] .more`)?.focus()
    } catch (e) {
      dialogError = errorText(e, "The paper wasn't moved")
    } finally {
      dialogBusy = false
    }
  }

  async function onDeletePaper() {
    const d = deleting
    if (!d) return
    dialogBusy = true
    dialogError = ''
    try {
      await deleteDocument(d.id)
      docs = docs.filter((x) => x.id !== d.id)
      announce = `Deleted “${titleOf(d)}”.`
      deleting = null
      await tick()
      heading?.focus()
    } catch (e) {
      dialogError = errorText(e, "The paper wasn't deleted")
    } finally {
      dialogBusy = false
    }
  }

  async function onRenameFolder(id: string, name: string): Promise<boolean> {
    clearError()
    try {
      const f = await renameFolder(id, name)
      folders = folders.map((x) => (x.id === id ? f : x)).sort(byName)
      announce = `Folder renamed to “${f.name}”.`
      return true
    } catch (e) {
      failed(e, "The folder wasn't renamed")
      return false
    }
  }

  async function onDeleteFolder() {
    const f = deletingFolder
    if (!f) return
    dialogBusy = true
    dialogError = ''
    try {
      await deleteFolder(f.id)
      folders = folders.filter((x) => x.id !== f.id)
      docs = docs.map((d) => (d.folder_id === f.id ? { ...d, folder_id: null } : d))
      if (collapsed.has(f.id)) toggleFolder(f.id)
      announce = `Folder “${f.name}” deleted. Its papers are in Unfiled.`
      deletingFolder = null
      await tick()
      heading?.focus()
    } catch (e) {
      dialogError = errorText(e, "The folder wasn't deleted")
    } finally {
      dialogBusy = false
    }
  }

  /** EXA-168: one PDF answer key for the folder's exam set. Empty placeholders are refused with
   *  the server's words and a "Download anyway". */
  async function downloadSetKey(f: Folder, allowPlaceholders = false) {
    clearError()
    setKeyFolder = f.id
    announce = `Making the answer key for “${f.name}”…`
    try {
      const url = URL.createObjectURL(await exportSetKey(f.id, allowPlaceholders))
      const a = document.createElement('a')
      a.href = url
      a.download = `${f.name} answer key.pdf`
      a.click()
      URL.revokeObjectURL(url)
      announce = `Downloaded the answer key for “${f.name}”.`
    } catch (e) {
      announce = ''
      if (setKeyUnfilled(e)) {
        error = errorText(e, "The set's answer key wasn't made")
        errorRetry = () => void downloadSetKey(f, true)
        errorRetryLabel = 'Download anyway'
      } else failed(e, "Couldn't download the set's answer key", () => void downloadSetKey(f, allowPlaceholders))
    } finally {
      setKeyFolder = null
    }
  }

  const grouped = $derived(groupByFolder(folders, docs))
  /** Each folder's exam-set status, from all its papers (not only those a search shows). */
  const setKeys = $derived(new Map(grouped.groups.map((g) => [g.folder.id, setKeyStatus(g.docs)])))
  const searching = $derived(query.trim() !== '')
  const shownGroups = $derived(
    searching
      ? grouped.groups
          .map((g) => ({ ...g, docs: g.docs.filter((d) => titleMatches(d.title, query)) }))
          .filter((g) => g.docs.length > 0)
      : grouped.groups,
  )
  const shownUnfiled = $derived(grouped.unfiled.filter((d) => titleMatches(d.title, query)))
  const matches = $derived(shownGroups.reduce((n, g) => n + g.docs.length, 0) + shownUnfiled.length)
  const folderPapers = $derived(deletingFolder ? docs.filter((d) => d.folder_id === deletingFolder?.id).length : 0)
  const papers = (n: number): string => `${n} ${n === 1 ? 'paper' : 'papers'}`

  // Say how many papers match as the search changes (an action's own message is left alone).
  $effect(() => {
    const q = query.trim()
    untrack(() => {
      if (q) announce = `${matches} ${matches === 1 ? 'paper matches' : 'papers match'} “${q}”.`
    })
  })
</script>

<main>
  <div class="masthead">
    <span class="wordmark">exam-paper-synthesis</span>
    <nav class="links" aria-label="More">
      {#if $settings?.classic_generator}<a class="classic" href="#/classic">Classic generator</a>{/if}
      <a class="classic" href="#/settings">Settings</a>
    </nav>
    <AccountMenu />
  </div>
  <div class="head">
    <h1 bind:this={heading} tabindex="-1">Your papers</h1>
    {#if docs.length > 0 || query}
      <label class="search">
        <Icon name="search" />
        <input
          type="search"
          bind:this={searchBox}
          bind:value={query}
          placeholder="Search papers"
          aria-label="Search papers"
          onkeydown={(e) => {
            if (e.key === 'Escape' && query) {
              e.preventDefault()
              query = ''
            }
          }}
        />
      </label>
    {/if}
    <button
      class="new"
      aria-haspopup="dialog"
      onclick={(e) => openWizard(e.currentTarget as HTMLElement)}>+ New</button
    >
  </div>

  {#if error}<ErrorNote message={error} onRetry={errorRetry} retryLabel={errorRetryLabel} />{/if}

  {#snippet row(d: DocumentSummary)}
    <PaperRow
      doc={d}
      {now}
      canMove={folders.length > 0}
      onRename={(t) => onRenamePaper(d, t)}
      onMove={() => {
        startDialog()
        moving = d
      }}
      onCopy={() => void onCopy(d)}
      onDelete={() => {
        startDialog()
        deleting = d
      }}
    />
  {/snippet}

  <p class="sr" role="status">{announce}</p>

  {#if !loaded}
    <div class="loading" role="status" data-testid="list-skeleton">
      <span class="visually-hidden">Loading your papers…</span>
      <ul class="docs loose" aria-hidden="true">
        {#each [62, 48, 70, 55] as w, i (i)}
          <li class="skel-row">
            <span class="skel" style:width="{w}%" style:height="14px"></span>
            <span class="skel" style:width="9rem" style:height="10px"></span>
          </li>
        {/each}
      </ul>
    </div>
  {:else if listError}
    <ErrorNote message={errorText(listError, "Couldn't load your papers")} onRetry={() => void refresh()} />
  {:else if docs.length === 0 && folders.length === 0}
    <p class="empty">No papers yet. Start with <b>+ New</b>: an exam set makes Booklet A, Booklet B and Paper 2 in one go.</p>
  {:else}
    {#if searching && matches === 0}
      <p class="empty">No papers match “{query.trim()}”.</p>
    {/if}
    {#if shownGroups.length > 0}
      <div class="folders">
        {#each shownGroups as g (g.folder.id)}
          <FolderSection
            group={g}
            collapsed={collapsed.has(g.folder.id)}
            collapsible={!searching}
            onToggle={() => toggleFolder(g.folder.id)}
            onRename={(name) => onRenameFolder(g.folder.id, name)}
            onDelete={() => {
              startDialog()
              deletingFolder = g.folder
            }}
            onNew={() => openWizard(document.activeElement as HTMLElement | null, g.folder)}
            setKey={setKeys.get(g.folder.id) ?? null}
            setKeyBusy={setKeyFolder === g.folder.id}
            onSetKey={() => void downloadSetKey(g.folder)}
          >
            <ul class="docs" aria-label={`Papers in “${g.folder.name}”`}>
              {#each g.docs as d (d.id)}{@render row(d)}{/each}
            </ul>
          </FolderSection>
        {/each}
      </div>
    {/if}

    {#if !searching || shownUnfiled.length > 0}
      <section class="unfiled" aria-labelledby={folders.length > 0 ? 'unfiled-h' : undefined}>
        {#if folders.length > 0}
          <h2 id="unfiled-h">Unfiled</h2>
          {#if shownUnfiled.length === 0}
            <p class="empty">Every paper is in a folder.</p>
          {/if}
        {/if}
        {#if shownUnfiled.length > 0}
          <ul class="docs loose" aria-label={folders.length > 0 ? 'Unfiled papers' : 'Papers'}>
            {#each shownUnfiled as d (d.id)}{@render row(d)}{/each}
          </ul>
        {/if}
      </section>
    {/if}
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

{#if moving}
  <MoveDialog
    {folders}
    current={folders.some((f) => f.id === moving?.folder_id) ? (moving.folder_id ?? null) : null}
    busy={dialogBusy}
    error={dialogError}
    onMove={(id) => void onMove(id)}
    onClose={() => (moving = null)}
  />
{/if}

{#if deleting}
  <ConfirmDialog
    title={`Delete “${titleOf(deleting)}”?`}
    body="The paper is deleted for good. This can’t be undone."
    confirmLabel="Delete paper"
    danger
    busy={dialogBusy}
    error={dialogError}
    onConfirm={() => void onDeletePaper()}
    onCancel={() => (deleting = null)}
  />
{/if}

{#if deletingFolder}
  <ConfirmDialog
    title={`Delete the folder “${deletingFolder.name}”?`}
    body={`${folderPapers > 0 ? `Its ${papers(folderPapers)} will move to Unfiled. ` : ''}No paper is deleted.`}
    confirmLabel="Delete folder"
    danger
    busy={dialogBusy}
    error={dialogError}
    onConfirm={() => void onDeleteFolder()}
    onCancel={() => (deletingFolder = null)}
  />
{/if}

<style>
  main {
    max-width: 760px;
    margin: 0 auto;
    padding: var(--s8) var(--s4) 4.5rem;
  }
  .masthead {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: var(--s6);
  }
  .wordmark {
    font-family: var(--mono);
    font-size: 13.5px;
    font-weight: 600;
  }
  .links {
    display: flex;
    gap: var(--s4);
    margin-left: auto;
    margin-right: var(--s4);
  }
  .classic {
    font-size: 12.5px;
    color: var(--ink-faint);
  }
  .head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--s3);
    margin-bottom: var(--s4);
  }
  h1 {
    flex: 1;
    margin: 0;
    font-size: 24px;
  }
  h1:focus {
    outline: none;
  }
  .search {
    display: flex;
    align-items: center;
    gap: 6px;
    width: 220px;
    height: 32px;
    box-sizing: border-box;
    padding: 0 10px;
    border: 1px solid var(--line);
    border-radius: var(--r-sm);
    background: var(--page);
    color: var(--ink-faint);
  }
  .search:focus-within {
    outline: 2px solid var(--verify);
    outline-offset: 1px;
  }
  .search input {
    flex: 1;
    min-width: 0;
    border: 0;
    outline: 0;
    background: none;
    font: inherit;
    font-size: 13px;
    color: var(--ink);
  }
  .new {
    font: inherit;
    font-size: 13.5px;
    font-weight: 600;
    height: 32px;
    border: 1px solid var(--verify);
    background: var(--verify);
    color: var(--on-accent);
    border-radius: var(--r-sm);
    padding: 0 var(--s3);
    cursor: pointer;
  }
  .new:hover {
    background: var(--verify-ink);
  }
  .new:focus-visible {
    outline: 2px solid var(--verify);
    outline-offset: 2px;
  }
  @media (max-width: 600px) {
    /* the search takes its own line under the title and + New */
    .search {
      order: 3;
      width: 100%;
    }
  }
  .folders {
    display: grid;
    gap: var(--s4);
  }
  .unfiled h2 {
    font-size: 13px;
    font-weight: 600;
    color: var(--ink-soft);
    margin: var(--s6) 0 var(--s2);
  }
  .unfiled .empty {
    margin: 0;
    font-size: 13px;
  }
  .docs {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  .loose {
    background: var(--page);
    border: 1px solid var(--line);
    border-radius: var(--r-md);
  }
  .loose :global(.row:first-child) {
    border-top-left-radius: calc(var(--r-md) - 1px);
    border-top-right-radius: calc(var(--r-md) - 1px);
  }
  .sr {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
  }
  .empty {
    color: var(--ink-soft);
  }
  .skel-row {
    display: grid;
    gap: var(--s2);
    align-content: center;
    min-height: 56px;
    padding: var(--s2) var(--s4);
    box-sizing: border-box;
    border-top: 1px solid var(--line-soft);
  }
  .skel-row:first-child {
    border-top: 0;
  }
</style>
