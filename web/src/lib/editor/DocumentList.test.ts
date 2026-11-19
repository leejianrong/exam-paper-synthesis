import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/svelte'

const listDocuments = vi.fn()
const createDocument = vi.fn()
const deleteDocument = vi.fn()
const listPaperTemplates = vi.fn()
const generatePaper = vi.fn()
const listFolders = vi.fn()
const createFolder = vi.fn()
const renameFolder = vi.fn()
const deleteFolder = vi.fn()
const moveDocument = vi.fn()
vi.mock('./docsApi', () => ({
  listFolders: (...a: unknown[]) => listFolders(...a),
  createFolder: (...a: unknown[]) => createFolder(...a),
  renameFolder: (...a: unknown[]) => renameFolder(...a),
  deleteFolder: (...a: unknown[]) => deleteFolder(...a),
  moveDocument: (...a: unknown[]) => moveDocument(...a),
  listDocuments: (...a: unknown[]) => listDocuments(...a),
  createDocument: (...a: unknown[]) => createDocument(...a),
  deleteDocument: (...a: unknown[]) => deleteDocument(...a),
  listPaperTemplates: (...a: unknown[]) => listPaperTemplates(...a),
  generatePaper: (...a: unknown[]) => generatePaper(...a),
}))

const TEMPLATES = {
  levels: ['P5', 'P6'],
  templates: [
    { code: 'p1_booklet_b', label: 'Paper 1 · Booklet B', title: 'Paper 1 Booklet B', time_min: 60, sections: [] },
    { code: 'p2', label: 'Paper 2', title: 'Paper 2', time_min: 90, sections: [] },
  ],
}

import DocumentList from './DocumentList.svelte'
import { lastReport } from './paperReport'
import { DEFAULT_SETTINGS, settings } from '../settings'

const summary = (id: string, title: string, folder_id: string | null = null) => ({
  id,
  title,
  folder_id,
  total_marks: 12,
  version: 3,
  created_at: '2026-10-08T00:00:00Z',
  updated_at: '2026-10-08T01:00:00Z',
})

beforeEach(() => {
  listDocuments.mockReset()
  createDocument.mockReset()
  deleteDocument.mockReset()
  generatePaper.mockReset()
  listPaperTemplates.mockReset()
  listPaperTemplates.mockResolvedValue(TEMPLATES)
  for (const m of [listFolders, createFolder, renameFolder, deleteFolder, moveDocument]) m.mockReset()
  listFolders.mockResolvedValue([])
  lastReport.set(null)
  location.hash = ''
})

describe('DocumentList', () => {
  it('lists papers with marks and links to the editor', async () => {
    listDocuments.mockResolvedValue([summary('d1', 'Ratio Review')])
    render(DocumentList)
    const link = await screen.findByRole('link', { name: /Ratio Review/ })
    expect(link).toHaveAttribute('href', '#/docs/d1')
    expect(link).toHaveTextContent('12 marks')
  })

  it('shows the empty state', async () => {
    listDocuments.mockResolvedValue([])
    render(DocumentList)
    expect(await screen.findByText(/No papers yet/)).toBeInTheDocument()
  })

  it('+ New opens the wizard; a blank paper opens in the editor; Escape gives focus back', async () => {
    listDocuments.mockResolvedValue([])
    createDocument.mockResolvedValue({ ...summary('new1', 'Untitled paper'), document: {} })
    render(DocumentList)
    const trigger = await screen.findByRole('button', { name: '+ New' })
    trigger.focus()
    await fireEvent.click(trigger)
    const dialog = await screen.findByRole('dialog', { name: 'New' })
    await fireEvent.keyDown(dialog, { key: 'Escape' })
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    await waitFor(() => expect(trigger).toHaveFocus())
    await fireEvent.click(trigger)
    await fireEvent.click(await screen.findByRole('button', { name: 'Blank paper' }))
    await waitFor(() => expect(location.hash).toBe('#/docs/new1'))
    expect(createDocument).toHaveBeenCalledWith(undefined, undefined, null)
  })

  it('deletes only after a second confirming click', async () => {
    listDocuments.mockResolvedValue([summary('d1', 'Ratio Review')])
    deleteDocument.mockResolvedValue(undefined)
    render(DocumentList)
    await fireEvent.click(await screen.findByRole('button', { name: 'Delete' }))
    expect(deleteDocument).not.toHaveBeenCalled()
    await fireEvent.click(screen.getByRole('button', { name: 'Confirm delete' }))
    await waitFor(() => expect(deleteDocument).toHaveBeenCalledWith('d1'))
    await waitFor(() => expect(screen.queryByText('Ratio Review')).not.toBeInTheDocument())
  })

  it('shows API errors', async () => {
    listDocuments.mockRejectedValue(new Error('API 401: authentication required'))
    render(DocumentList)
    expect(await screen.findByRole('alert')).toHaveTextContent('authentication required')
  })

  it('makes an exam set into a new folder, adds the papers and shows the folder (O3)', async () => {
    listDocuments.mockResolvedValue([])
    createFolder.mockResolvedValue(folder('fs', 'P6 exam set'))
    const parts = { p1_booklet_a: 'booklet_a', p1_booklet_b: 'booklet_b', p2: 'paper_2' } as const
    createDocument.mockImplementation(async (_t: unknown, code: keyof typeof parts, fid: string) => ({
      ...summary(`d-${code}`, 'Renamed', fid),
      paper_part: parts[code],
      document: {},
    }))
    render(DocumentList)
    await fireEvent.click(await screen.findByRole('button', { name: '+ New' }))
    await fireEvent.click(await screen.findByRole('button', { name: 'Exam set' }))
    await fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    await fireEvent.click(await screen.findByRole('button', { name: 'Empty starters' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    const chips = await screen.findByRole('list', { name: 'Exam set in “P6 exam set”' })
    // Titled "Renamed": the chips come from the server's paper_part, not the title.
    expect(within(chips).getAllByRole('listitem').map((li) => li.classList.contains('on'))).toEqual([true, true, true])
    await waitFor(() => expect(screen.getByRole('heading', { name: 'P6 exam set' })).toHaveFocus())
    expect(screen.getByRole('status')).toHaveTextContent('Folder “P6 exam set” created.')
  })

  it('a folder’s “+ New in folder” files what the wizard makes there', async () => {
    listFolders.mockResolvedValue([folder('f1', 'Prelims 2026')])
    listDocuments.mockResolvedValue([])
    createDocument.mockResolvedValue({ ...summary('t1', 'Paper 2', 'f1'), document: {} })
    render(DocumentList)
    const here = await screen.findByRole('button', { name: '+ New in folder “Prelims 2026”' })
    await fireEvent.click(here)
    const dialog = await screen.findByRole('dialog', { name: 'New' })
    expect(dialog).toHaveTextContent('Papers go in Prelims 2026.')
    await fireEvent.click(within(dialog).getByRole('button', { name: 'Single paper' }))
    await fireEvent.click(await screen.findByRole('button', { name: 'Paper 2' }))
    await fireEvent.click(await screen.findByRole('button', { name: 'Start it empty' }))
    await waitFor(() => expect(location.hash).toBe('#/docs/t1'))
    expect(createDocument).toHaveBeenCalledWith(undefined, 'p2', 'f1')
  })

  it('hides the Classic generator link unless the setting is on (O1); Settings is always there', async () => {
    listDocuments.mockResolvedValue([])
    settings.set({ ...DEFAULT_SETTINGS, classic_generator: false })
    const { unmount } = render(DocumentList)
    expect(await screen.findByRole('link', { name: 'Settings' })).toHaveAttribute('href', '#/settings')
    expect(screen.queryByRole('link', { name: 'Classic generator' })).toBeNull()
    unmount()
    settings.set({ ...DEFAULT_SETTINGS, classic_generator: true })
    render(DocumentList)
    expect(await screen.findByRole('link', { name: 'Classic generator' })).toHaveAttribute('href', '#/classic')
  })
})

const folder = (id: string, name: string) => ({
  id,
  name,
  created_at: '2026-11-01T00:00:00Z',
  updated_at: '2026-11-01T00:00:00Z',
})

const section = (name: string) => screen.getByRole('region', { name })

describe('DocumentList folders (O2)', () => {
  it('groups papers by folder in the API order, then Unfiled', async () => {
    listFolders.mockResolvedValue([folder('f2', 'Term 1'), folder('f1', 'Prelims 2026')])
    listDocuments.mockResolvedValue([
      summary('d1', 'P6 Paper 2', 'f1'),
      summary('d2', 'Fractions drill'),
      summary('d3', 'Ratio quiz', 'f2'),
      summary('d4', 'Old copy', 'gone'),
    ])
    render(DocumentList)
    await screen.findByRole('heading', { name: 'Term 1' })
    const headings = screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent)
    expect(headings).toEqual(['Term 1', 'Prelims 2026', 'Unfiled'])
    expect(within(section('Prelims 2026')).getByRole('link', { name: /P6 Paper 2/ })).toBeInTheDocument()
    expect(within(section('Term 1')).getByRole('link', { name: /Ratio quiz/ })).toBeInTheDocument()
    const unfiled = within(section('Unfiled'))
    expect(unfiled.getByRole('link', { name: /Fractions drill/ })).toBeInTheDocument()
    // A paper whose folder no longer exists is shown as unfiled.
    expect(unfiled.getByRole('link', { name: /Old copy/ })).toBeInTheDocument()
  })

  it('fills an exam-set chip when the folder holds a paper of that part', async () => {
    listFolders.mockResolvedValue([folder('f1', 'Prelims 2026')])
    listDocuments.mockResolvedValue([
      summary('d1', 'P6 Paper 1 Booklet A', 'f1'),
      summary('d2', 'P6 Paper 2', 'f1'),
    ])
    render(DocumentList)
    const chips = await screen.findByRole('list', { name: 'Exam set in “Prelims 2026”' })
    const items = within(chips).getAllByRole('listitem')
    expect(items.map((li) => li.dataset.part)).toEqual(['booklet_a', 'booklet_b', 'paper_2'])
    expect(items.map((li) => li.classList.contains('on'))).toEqual([true, false, true])
    expect(items[0]).toHaveTextContent('Booklet A: in this folder')
    expect(items[1]).toHaveTextContent('Booklet B: not in this folder yet')
  })

  it('says when a folder is empty, and there is no Move menu without folders', async () => {
    listDocuments.mockResolvedValue([summary('d1', 'Ratio Review')])
    const { unmount } = render(DocumentList)
    await screen.findByRole('link', { name: /Ratio Review/ })
    expect(screen.queryByRole('button', { name: /Move/ })).toBeNull()
    expect(screen.queryByRole('heading', { name: 'Unfiled' })).toBeNull()
    unmount()
    listFolders.mockResolvedValue([folder('f1', 'Term 1')])
    render(DocumentList)
    expect(await screen.findByText(/No papers in this folder yet/)).toBeInTheDocument()
  })

  it('creates a folder from the wizard and focuses it in the list', async () => {
    listDocuments.mockResolvedValue([])
    createFolder.mockResolvedValue(folder('f1', 'Prelims 2026'))
    render(DocumentList)
    await fireEvent.click(await screen.findByRole('button', { name: '+ New' }))
    await fireEvent.click(await screen.findByRole('button', { name: 'New folder' }))
    const input = screen.getByRole('textbox', { name: 'Folder name' })
    await waitFor(() => expect(input).toHaveFocus())
    await fireEvent.input(input, { target: { value: '  Prelims 2026 ' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Create folder' }))
    await waitFor(() => expect(createFolder).toHaveBeenCalledWith('Prelims 2026'))
    expect(await screen.findByRole('heading', { name: 'Prelims 2026' })).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(screen.getByRole('status')).toHaveTextContent('Folder “Prelims 2026” created.')
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Prelims 2026' })).toHaveFocus())
  })

  it('moves a paper into a folder from its Move menu, by keyboard', async () => {
    listFolders.mockResolvedValue([folder('f1', 'Prelims 2026'), folder('f2', 'Term 1')])
    listDocuments.mockResolvedValue([summary('d1', 'P6 Paper 1 Booklet B')])
    moveDocument.mockResolvedValue(summary('d1', 'P6 Paper 1 Booklet B', 'f2'))
    render(DocumentList)
    const trigger = await screen.findByRole('button', { name: 'Move “P6 Paper 1 Booklet B” to a folder' })
    expect(trigger).toHaveAttribute('aria-expanded', 'false')
    await fireEvent.keyDown(trigger, { key: 'ArrowDown' })
    const menu = await screen.findByRole('menu', { name: 'Move to' })
    const items = within(menu).getAllByRole('menuitemradio')
    expect(items.map((i) => i.textContent?.replace('✓', '').trim())).toEqual(['Prelims 2026', 'Term 1', 'Unfiled'])
    // Opens on the current place (Unfiled); the arrows wrap round to the folders.
    await waitFor(() => expect(items[2]).toHaveFocus())
    expect(items[2]).toHaveAttribute('aria-checked', 'true')
    await fireEvent.keyDown(menu, { key: 'ArrowDown' })
    expect(items[0]).toHaveFocus()
    await fireEvent.keyDown(menu, { key: 'ArrowDown' })
    expect(items[1]).toHaveFocus()
    await fireEvent.click(items[1])
    await waitFor(() => expect(moveDocument).toHaveBeenCalledWith('d1', 'f2'))
    const chips = await screen.findByRole('list', { name: 'Exam set in “Term 1”' })
    await waitFor(() => expect(within(chips).getByText(/Booklet B/).closest('li')).toHaveClass('on'))
    expect(within(section('Term 1')).getByRole('link', { name: /P6 Paper 1 Booklet B/ })).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Moved “P6 Paper 1 Booklet B” to “Term 1”.')
    expect(screen.queryByRole('menu')).toBeNull()
  })

  it('moves a paper back to Unfiled; Escape closes the menu without moving', async () => {
    listFolders.mockResolvedValue([folder('f1', 'Prelims 2026')])
    listDocuments.mockResolvedValue([summary('d1', 'Ratio quiz', 'f1')])
    moveDocument.mockResolvedValue(summary('d1', 'Ratio quiz', null))
    render(DocumentList)
    const trigger = await screen.findByRole('button', { name: 'Move “Ratio quiz” to a folder' })
    await fireEvent.click(trigger)
    const menu = await screen.findByRole('menu')
    await fireEvent.keyDown(menu, { key: 'Escape' })
    expect(screen.queryByRole('menu')).toBeNull()
    expect(trigger).toHaveFocus()
    expect(moveDocument).not.toHaveBeenCalled()
    await fireEvent.click(trigger)
    await fireEvent.click(await screen.findByRole('menuitemradio', { name: /Unfiled/ }))
    await waitFor(() => expect(moveDocument).toHaveBeenCalledWith('d1', null))
    await waitFor(() =>
      expect(within(section('Unfiled')).getByRole('link', { name: /Ratio quiz/ })).toBeInTheDocument(),
    )
  })

  it('renames a folder inline', async () => {
    listFolders.mockResolvedValue([folder('f1', 'Prelims')])
    listDocuments.mockResolvedValue([])
    renameFolder.mockResolvedValue(folder('f1', 'Prelims 2026'))
    render(DocumentList)
    await fireEvent.click(await screen.findByRole('button', { name: 'Rename folder “Prelims”' }))
    const input = screen.getByRole('textbox', { name: 'Folder name' })
    expect(input).toHaveValue('Prelims')
    await fireEvent.input(input, { target: { value: 'Prelims 2026' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(renameFolder).toHaveBeenCalledWith('f1', 'Prelims 2026'))
    expect(await screen.findByRole('heading', { name: 'Prelims 2026' })).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Rename folder “Prelims 2026”' })).toHaveFocus())
  })

  it('keeps the rename field open and shows the error when the rename fails', async () => {
    listFolders.mockResolvedValue([folder('f1', 'Prelims')])
    listDocuments.mockResolvedValue([])
    renameFolder.mockRejectedValue(new Error('API 422: name must be 1-80 characters'))
    render(DocumentList)
    await fireEvent.click(await screen.findByRole('button', { name: 'Rename folder “Prelims”' }))
    await fireEvent.input(screen.getByRole('textbox', { name: 'Folder name' }), { target: { value: 'X' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('1-80 characters')
    expect(screen.getByRole('textbox', { name: 'Folder name' })).toBeInTheDocument()
  })

  it('deletes a folder only after confirming, and its papers become unfiled', async () => {
    listFolders.mockResolvedValue([folder('f1', 'Prelims 2026')])
    listDocuments.mockResolvedValue([
      summary('d1', 'P6 Paper 2', 'f1'),
      summary('d2', 'P6 Paper 1 Booklet A', 'f1'),
    ])
    deleteFolder.mockResolvedValue(undefined)
    render(DocumentList)
    await fireEvent.click(await screen.findByRole('button', { name: 'Delete folder “Prelims 2026”' }))
    expect(deleteFolder).not.toHaveBeenCalled()
    const confirm = screen.getByRole('group', { name: 'Delete folder “Prelims 2026”?' })
    expect(confirm).toHaveTextContent('Its 2 papers will move to Unfiled. No paper is deleted.')
    // Cancel keeps it.
    await fireEvent.click(within(confirm).getByRole('button', { name: 'Cancel' }))
    expect(screen.queryByRole('group', { name: /Delete folder/ })).toBeNull()
    await fireEvent.click(screen.getByRole('button', { name: 'Delete folder “Prelims 2026”' }))
    await fireEvent.click(screen.getByRole('button', { name: 'Delete folder' }))
    await waitFor(() => expect(deleteFolder).toHaveBeenCalledWith('f1'))
    await waitFor(() => expect(screen.queryByRole('heading', { name: 'Prelims 2026' })).toBeNull())
    // No folders left: the papers are listed (unfiled), none deleted.
    expect(screen.getByRole('link', { name: /P6 Paper 2/ })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /P6 Paper 1 Booklet A/ })).toBeInTheDocument()
    expect(deleteDocument).not.toHaveBeenCalled()
    expect(screen.getByRole('status')).toHaveTextContent('Folder “Prelims 2026” deleted. Its papers are in Unfiled.')
  })

  it('shows a loading state until the papers arrive', async () => {
    let resolve: (v: unknown) => void = () => {}
    listDocuments.mockReturnValue(new Promise((r) => (resolve = r)))
    render(DocumentList)
    expect(screen.getByText('Loading your papers…')).toBeInTheDocument()
    resolve([summary('d1', 'Ratio Review')])
    expect(await screen.findByRole('link', { name: /Ratio Review/ })).toBeInTheDocument()
    expect(screen.queryByText('Loading your papers…')).toBeNull()
  })
})
