import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
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
const renameDocument = vi.fn()
const copyDocument = vi.fn()
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
  renameDocument: (...a: unknown[]) => renameDocument(...a),
  copyDocument: (...a: unknown[]) => copyDocument(...a),
}))

const TEMPLATES = {
  levels: ['P5', 'P6'],
  templates: [
    { code: 'p1_booklet_b', label: 'Paper 1 · Booklet B', title: 'Paper 1 Booklet B', time_min: 60, sections: [] },
    { code: 'p2', label: 'Paper 2', title: 'Paper 2', time_min: 90, sections: [] },
  ],
}

import DocumentList from './DocumentList.svelte'
import { ApiError } from '../errors'
import { lastReport } from './paperReport'

const summary = (id: string, title: string, folder_id: string | null = null) => ({
  id,
  title,
  folder_id,
  total_marks: 12,
  version: 3,
  created_at: '2026-10-08T00:00:00Z',
  updated_at: '2026-10-08T01:00:00Z',
})

const folder = (id: string, name: string) => ({
  id,
  name,
  created_at: '2026-11-01T00:00:00Z',
  updated_at: '2026-11-01T00:00:00Z',
})

const section = (name: string) => screen.getByRole('region', { name })
const actions = (title: string) => screen.getByRole('button', { name: `Actions for “${title}”` })

/** Open a paper's ⋯ menu by keyboard and choose an item. */
async function choose(title: string, item: string) {
  const trigger = await screen.findByRole('button', { name: `Actions for “${title}”` })
  await fireEvent.keyDown(trigger, { key: 'ArrowDown' })
  const menu = await screen.findByRole('menu', { name: title })
  await fireEvent.click(within(menu).getByRole('menuitem', { name: item }))
}

beforeEach(() => {
  for (const m of [
    listDocuments,
    createDocument,
    deleteDocument,
    generatePaper,
    listPaperTemplates,
    listFolders,
    createFolder,
    renameFolder,
    deleteFolder,
    moveDocument,
    renameDocument,
    copyDocument,
  ])
    m.mockReset()
  listPaperTemplates.mockResolvedValue(TEMPLATES)
  listFolders.mockResolvedValue([])
  lastReport.set(null)
  location.hash = ''
  localStorage.clear()
})

afterEach(() => vi.restoreAllMocks())

describe('DocumentList', () => {
  it('lists papers with marks and an en-SG edit time, linking to the editor', async () => {
    listDocuments.mockResolvedValue([summary('d1', 'Ratio Review')])
    render(DocumentList)
    const link = await screen.findByRole('link', { name: /Ratio Review/ })
    expect(link).toHaveAttribute('href', '#/docs/d1')
    expect(link).toHaveTextContent('12 marks · edited')
    const time = link.querySelector('time')!
    expect(time).toHaveAttribute('datetime', '2026-10-08T01:00:00Z')
    // an old edit shows the date, the en-SG way (day month year, lower-case am/pm)
    expect(time.textContent).toMatch(/^8 Oct 2026, \d{1,2}:\d{2} [ap]m$/)
    expect(time.getAttribute('title')).toBe(time.textContent)
  })

  it('shows the empty state, naming the exam set', async () => {
    listDocuments.mockResolvedValue([])
    render(DocumentList)
    expect(await screen.findByText(/No papers yet/)).toHaveTextContent('an exam set makes Booklet A, Booklet B and Paper 2')
    expect(screen.queryByRole('searchbox')).toBeNull()
  })

  it('+ New opens the wizard on Exam set; a blank paper opens in the editor; Escape gives focus back', async () => {
    listDocuments.mockResolvedValue([])
    createDocument.mockResolvedValue({ ...summary('new1', 'Untitled paper'), document: {} })
    render(DocumentList)
    const trigger = await screen.findByRole('button', { name: '+ New' })
    trigger.focus()
    await fireEvent.click(trigger)
    const dialog = await screen.findByRole('dialog', { name: 'New' })
    await waitFor(() => expect(within(dialog).getByRole('button', { name: 'Exam set' })).toHaveFocus())
    await fireEvent.keyDown(dialog, { key: 'Escape' })
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    await waitFor(() => expect(trigger).toHaveFocus())
    await fireEvent.click(trigger)
    await fireEvent.click(await screen.findByRole('button', { name: 'Blank paper' }))
    await waitFor(() => expect(location.hash).toBe('#/docs/new1'))
    expect(createDocument).toHaveBeenCalledWith(undefined, undefined, null)
  })

  it('shows a skeleton while the papers load, then the list', async () => {
    let answer: (v: unknown) => void = () => {}
    listDocuments.mockReturnValue(new Promise((r) => (answer = r)))
    render(DocumentList)
    const skeleton = screen.getByTestId('list-skeleton')
    expect(skeleton).toHaveAttribute('role', 'status')
    expect(skeleton).not.toHaveAttribute('aria-busy') // a busy live region would hold back its own text
    expect(skeleton).toHaveTextContent('Loading your papers…')
    answer([summary('d1', 'Ratio Review')])
    expect(await screen.findByRole('link', { name: /Ratio Review/ })).toBeInTheDocument()
    expect(screen.queryByTestId('list-skeleton')).toBeNull()
  })

  it("a list that didn't load says why in words, with Try again (EXA-165)", async () => {
    listDocuments.mockRejectedValueOnce(new ApiError(500, 'boom')).mockResolvedValue([summary('d1', 'Ratio Review')])
    render(DocumentList)
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent("Couldn't load your papers. Something went wrong on our side.")
    expect(alert).not.toHaveTextContent('500')
    expect(screen.queryByText(/No papers yet/)).toBeNull()
    await fireEvent.click(within(alert).getByRole('button', { name: 'Try again' }))
    expect(await screen.findByRole('link', { name: /Ratio Review/ })).toBeInTheDocument()
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it("offline says the server can't be reached", async () => {
    listDocuments.mockRejectedValue(new ApiError(0, 'TypeError: Failed to fetch'))
    render(DocumentList)
    expect(await screen.findByRole('alert')).toHaveTextContent("Couldn't load your papers. Can't reach the server.")
  })

  it('makes an exam set into a new folder and shows the folder, without exam-set ticks', async () => {
    listDocuments.mockResolvedValue([])
    createFolder.mockResolvedValue(folder('fs', 'P6 exam set'))
    createDocument.mockImplementation(async (_t: unknown, code: string, fid: string) => ({
      ...summary(`d-${code}`, `Paper ${code}`, fid),
      document: {},
    }))
    render(DocumentList)
    await fireEvent.click(await screen.findByRole('button', { name: '+ New' }))
    await fireEvent.click(await screen.findByRole('button', { name: 'Exam set' }))
    await fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    await fireEvent.click(await screen.findByRole('button', { name: 'Empty starters' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    const toggle = await screen.findByRole('button', { name: 'P6 exam set', expanded: true })
    await waitFor(() => expect(toggle).toHaveFocus())
    expect(within(section('P6 exam set')).getAllByRole('link')).toHaveLength(3)
    // EXA-166 (owner decision): no Booklet A / Booklet B / Paper 2 ticks on the folder.
    expect(screen.queryByRole('list', { name: /Exam set in/ })).toBeNull()
    expect(section('P6 exam set')).not.toHaveTextContent('Booklet A')
    expect(screen.getByRole('status')).toHaveTextContent('Folder “P6 exam set” created.')
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

describe('DocumentList: a paper’s ⋯ menu (EXA-166)', () => {
  it('replaces the loose row buttons; it opens by keyboard with the five actions, Delete last', async () => {
    listDocuments.mockResolvedValue([summary('d1', 'Ratio Review')])
    render(DocumentList)
    const trigger = await screen.findByRole('button', { name: 'Actions for “Ratio Review”' })
    expect(screen.queryByRole('button', { name: 'Delete' })).toBeNull()
    expect(screen.queryByRole('button', { name: /^Move/ })).toBeNull()
    expect(trigger).toHaveAttribute('aria-haspopup', 'menu')
    await fireEvent.keyDown(trigger, { key: 'ArrowDown' })
    const menu = await screen.findByRole('menu', { name: 'Ratio Review' })
    const rows = within(menu).getAllByRole('menuitem')
    expect(rows.map((r) => r.textContent?.trim())).toEqual(['Open', 'Rename', 'Move to folder…', 'Make a copy', 'Delete…'])
    await waitFor(() => expect(rows[0]).toHaveFocus())
    // no folder to move to yet: Move says why it is off
    expect(rows[2]).toHaveAttribute('aria-disabled', 'true')
    expect(rows[2]).toHaveAttribute('title', 'Make a folder first, with + New.')
    expect(rows[4]).toHaveClass('danger')
    await fireEvent.keyDown(menu, { key: 'Escape' })
    expect(screen.queryByRole('menu')).toBeNull()
    expect(trigger).toHaveFocus()
  })

  it('Shift+F10 on the paper’s link opens its menu', async () => {
    listDocuments.mockResolvedValue([summary('d1', 'Ratio Review')])
    render(DocumentList)
    const link = await screen.findByRole('link', { name: /Ratio Review/ })
    await fireEvent.keyDown(link, { key: 'F10', shiftKey: true })
    expect(await screen.findByRole('menu', { name: 'Ratio Review' })).toBeInTheDocument()
  })

  it('Open goes to the editor', async () => {
    listDocuments.mockResolvedValue([summary('d1', 'Ratio Review')])
    render(DocumentList)
    await choose('Ratio Review', 'Open')
    expect(location.hash).toBe('#/docs/d1')
  })

  it('Delete asks in a dialog; Cancel keeps the paper, Delete paper deletes it', async () => {
    listDocuments.mockResolvedValue([summary('d1', 'Ratio Review'), summary('d2', 'Fractions drill')])
    deleteDocument.mockResolvedValue(undefined)
    render(DocumentList)
    await choose('Ratio Review', 'Delete…')
    let dialog = await screen.findByRole('alertdialog', { name: 'Delete “Ratio Review”?' })
    await fireEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }))
    expect(screen.queryByRole('alertdialog')).toBeNull()
    expect(deleteDocument).not.toHaveBeenCalled()
    await waitFor(() => expect(actions('Ratio Review')).toHaveFocus())
    await choose('Ratio Review', 'Delete…')
    dialog = await screen.findByRole('alertdialog', { name: 'Delete “Ratio Review”?' })
    await fireEvent.click(within(dialog).getByRole('button', { name: 'Delete paper' }))
    await waitFor(() => expect(deleteDocument).toHaveBeenCalledWith('d1'))
    await waitFor(() => expect(screen.queryByRole('link', { name: /Ratio Review/ })).toBeNull())
    expect(screen.getByRole('link', { name: /Fractions drill/ })).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Deleted “Ratio Review”.')
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Your papers' })).toHaveFocus())
  })

  it('a failed delete keeps the dialog open with the error', async () => {
    listDocuments.mockResolvedValue([summary('d1', 'Ratio Review')])
    deleteDocument.mockRejectedValue(new ApiError(500, 'boom'))
    render(DocumentList)
    await choose('Ratio Review', 'Delete…')
    const dialog = await screen.findByRole('alertdialog')
    await fireEvent.click(within(dialog).getByRole('button', { name: 'Delete paper' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent(
      "The paper wasn't deleted. Something went wrong on our side.",
    )
    expect(within(dialog).getByRole('alert')).not.toHaveTextContent('boom')
    expect(screen.getByRole('link', { name: /Ratio Review/ })).toBeInTheDocument()
  })

  it('Rename edits the title in place; Enter saves and focus goes back to the ⋯ button', async () => {
    listDocuments.mockResolvedValue([summary('d1', 'Ratio Review')])
    renameDocument.mockResolvedValue({ ...summary('d1', 'Ratio review (Term 3)'), version: 4, document: {} })
    render(DocumentList)
    await choose('Ratio Review', 'Rename')
    const input = await screen.findByRole('textbox', { name: 'Paper title' })
    expect(input).toHaveValue('Ratio Review')
    await waitFor(() => expect(input).toHaveFocus())
    await fireEvent.input(input, { target: { value: '  Ratio review (Term 3) ' } })
    await fireEvent.submit(input.closest('form')!)
    await waitFor(() => expect(renameDocument).toHaveBeenCalledWith('d1', 'Ratio review (Term 3)'))
    expect(await screen.findByRole('link', { name: /Ratio review \(Term 3\)/ })).toBeInTheDocument()
    await waitFor(() => expect(actions('Ratio review (Term 3)')).toHaveFocus())
    expect(screen.getByRole('status')).toHaveTextContent('Renamed to “Ratio review (Term 3)”.')
  })

  it('Escape backs out of a rename; a failed rename keeps the field and shows why', async () => {
    listDocuments.mockResolvedValue([summary('d1', 'Ratio Review')])
    renameDocument.mockRejectedValue(new ApiError(409, { message: 'document changed elsewhere', current_version: 5 }))
    render(DocumentList)
    await choose('Ratio Review', 'Rename')
    let input = await screen.findByRole('textbox', { name: 'Paper title' })
    await fireEvent.keyDown(input, { key: 'Escape' })
    expect(screen.queryByRole('textbox', { name: 'Paper title' })).toBeNull()
    await waitFor(() => expect(actions('Ratio Review')).toHaveFocus())
    expect(renameDocument).not.toHaveBeenCalled()
    await choose('Ratio Review', 'Rename')
    input = await screen.findByRole('textbox', { name: 'Paper title' })
    await fireEvent.input(input, { target: { value: 'New name' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByRole('alert')).toHaveTextContent("The paper wasn't renamed. This paper changed in another tab or window.")
    expect(screen.getByRole('textbox', { name: 'Paper title' })).toBeInTheDocument()
  })

  it('a copy whose reply was lost offers no Try again and says to check the list (EXA-165)', async () => {
    listDocuments.mockResolvedValue([summary('d1', 'Ratio Review')])
    copyDocument.mockRejectedValue(new ApiError(0, 'TypeError: Failed to fetch'))
    render(DocumentList)
    await choose('Ratio Review', 'Make a copy')
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent("Couldn't make a copy. Can't reach the server. Check your internet connection. Check Your papers before trying again.")
    expect(within(alert).queryByRole('button', { name: 'Try again' })).toBeNull()
    expect(copyDocument).toHaveBeenCalledTimes(1)
  })

  it('Make a copy adds “Copy of …” under the paper, in the same folder', async () => {
    listFolders.mockResolvedValue([folder('f1', 'Prelims 2026')])
    listDocuments.mockResolvedValue([summary('d1', 'P6 Paper 2', 'f1'), summary('d2', 'Ratio quiz', 'f1')])
    copyDocument.mockResolvedValue({ ...summary('c1', 'Copy of P6 Paper 2', 'f1'), version: 2, document: {} })
    render(DocumentList)
    await choose('P6 Paper 2', 'Make a copy')
    await waitFor(() => expect(copyDocument).toHaveBeenCalledWith('d1'))
    const links = await within(section('Prelims 2026')).findAllByRole('link')
    await waitFor(() =>
      expect(within(section('Prelims 2026')).getAllByRole('link').map((l) => l.querySelector('.t')?.textContent)).toEqual([
        'P6 Paper 2',
        'Copy of P6 Paper 2',
        'Ratio quiz',
      ]),
    )
    expect(links.length).toBeGreaterThan(0)
    expect(screen.getByRole('status')).toHaveTextContent('Made “Copy of P6 Paper 2”.')
  })

  it('Move to folder… picks a folder in a dialog and files the paper there', async () => {
    listFolders.mockResolvedValue([folder('f1', 'Prelims 2026'), folder('f2', 'Term 1')])
    listDocuments.mockResolvedValue([summary('d1', 'P6 Paper 1 Booklet B')])
    moveDocument.mockResolvedValue(summary('d1', 'P6 Paper 1 Booklet B', 'f2'))
    render(DocumentList)
    await choose('P6 Paper 1 Booklet B', 'Move to folder…')
    const dialog = await screen.findByRole('dialog', { name: 'Move to folder' })
    expect(within(dialog).getByRole('radio', { name: 'Unfiled' })).toBeChecked()
    await fireEvent.click(within(dialog).getByRole('radio', { name: 'Term 1' }))
    await fireEvent.click(within(dialog).getByRole('button', { name: 'Move' }))
    await waitFor(() => expect(moveDocument).toHaveBeenCalledWith('d1', 'f2'))
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    expect(within(section('Term 1')).getByRole('link', { name: /P6 Paper 1 Booklet B/ })).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Moved “P6 Paper 1 Booklet B” to “Term 1”.')
    await waitFor(() => expect(actions('P6 Paper 1 Booklet B')).toHaveFocus())
  })

  it('moves a paper back to Unfiled', async () => {
    listFolders.mockResolvedValue([folder('f1', 'Prelims 2026')])
    listDocuments.mockResolvedValue([summary('d1', 'Ratio quiz', 'f1')])
    moveDocument.mockResolvedValue(summary('d1', 'Ratio quiz', null))
    render(DocumentList)
    await choose('Ratio quiz', 'Move to folder…')
    const dialog = await screen.findByRole('dialog', { name: 'Move to folder' })
    await fireEvent.click(within(dialog).getByRole('radio', { name: 'Unfiled' }))
    await fireEvent.click(within(dialog).getByRole('button', { name: 'Move' }))
    await waitFor(() => expect(moveDocument).toHaveBeenCalledWith('d1', null))
    await waitFor(() =>
      expect(within(section('Unfiled')).getByRole('link', { name: /Ratio quiz/ })).toBeInTheDocument(),
    )
  })

  it('the Move dialog stays open while the move runs, so a failure still shows', async () => {
    listFolders.mockResolvedValue([folder('f1', 'Prelims 2026')])
    listDocuments.mockResolvedValue([summary('d1', 'Ratio quiz')])
    let fail: (e: Error) => void = () => {}
    moveDocument.mockReturnValue(new Promise((_, reject) => (fail = reject)))
    render(DocumentList)
    await choose('Ratio quiz', 'Move to folder…')
    const dialog = await screen.findByRole('dialog', { name: 'Move to folder' })
    await fireEvent.click(within(dialog).getByRole('radio', { name: 'Prelims 2026' }))
    await fireEvent.click(within(dialog).getByRole('button', { name: 'Move' }))
    await fireEvent.keyDown(dialog, { key: 'Escape' })
    await fireEvent.click(within(dialog).getByRole('button', { name: 'Close' }))
    expect(screen.getByRole('dialog', { name: 'Move to folder' })).toBeInTheDocument()
    fail(new ApiError(500, 'boom'))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent("The paper wasn't moved. Something went wrong on our side.")
    // once it has failed the dialog closes again
    await fireEvent.keyDown(dialog, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('a right-click on the row opens the menu; on the title link the browser keeps its own', async () => {
    listDocuments.mockResolvedValue([summary('d1', 'Ratio Review')])
    render(DocumentList)
    const link = await screen.findByRole('link', { name: /Ratio Review/ })
    // fireEvent returns false when the event's default was prevented
    expect(await fireEvent.contextMenu(link)).toBe(true)
    expect(screen.queryByRole('menu')).toBeNull()
    expect(await fireEvent.contextMenu(link.closest('li')!)).toBe(false)
    expect(await screen.findByRole('menu', { name: 'Ratio Review' })).toBeInTheDocument()
  })
})

describe('DocumentList: search (EXA-166)', () => {
  it('filters papers by title, hides folders without a match, and Escape clears it', async () => {
    listFolders.mockResolvedValue([folder('f1', 'Prelims 2026'), folder('f2', 'Term 1')])
    listDocuments.mockResolvedValue([
      summary('d1', 'P6 Paper 1 Booklet A', 'f1'),
      summary('d2', 'P6 Paper 2', 'f1'),
      summary('d3', 'Ratio quiz', 'f2'),
      summary('d4', 'Booklet A drill'),
    ])
    render(DocumentList)
    const box = await screen.findByRole('searchbox', { name: 'Search papers' })
    await fireEvent.input(box, { target: { value: 'booklet a' } })
    expect(screen.getAllByRole('link', { name: /Booklet A/ })).toHaveLength(2)
    expect(screen.queryByRole('link', { name: /P6 Paper 2/ })).toBeNull()
    expect(screen.queryByRole('region', { name: 'Term 1' })).toBeNull()
    // while searching a folder shows its matches and its name is not a collapse button
    expect(screen.queryByRole('button', { name: 'Prelims 2026' })).toBeNull()
    expect(screen.getByRole('heading', { name: 'Prelims 2026' })).toBeInTheDocument()
    expect(within(section('Unfiled')).getByRole('link', { name: /Booklet A drill/ })).toBeInTheDocument()

    await fireEvent.input(box, { target: { value: 'fractions' } })
    expect(screen.getByText('No papers match “fractions”.')).toBeInTheDocument()
    expect(screen.queryAllByRole('link', { name: /Paper|quiz|drill/ })).toHaveLength(0)

    await fireEvent.keyDown(box, { key: 'Escape' })
    expect(box).toHaveValue('')
    expect(screen.getAllByRole('link', { name: /Paper|quiz|drill/ })).toHaveLength(4)
  })

  it('shows a collapsed folder’s matches while searching', async () => {
    localStorage.setItem('exam.papers.collapsed', JSON.stringify(['f1']))
    listFolders.mockResolvedValue([folder('f1', 'Prelims 2026')])
    listDocuments.mockResolvedValue([summary('d1', 'P6 Paper 2', 'f1')])
    render(DocumentList)
    await screen.findByRole('button', { name: 'Prelims 2026', expanded: false })
    expect(screen.queryByRole('link', { name: /P6 Paper 2/ })).toBeNull()
    await fireEvent.input(screen.getByRole('searchbox'), { target: { value: 'paper' } })
    expect(screen.getByRole('link', { name: /P6 Paper 2/ })).toBeInTheDocument()
  })

  it('counts matches in the folder header and announces how many papers match', async () => {
    listFolders.mockResolvedValue([folder('f1', 'Prelims 2026')])
    listDocuments.mockResolvedValue([
      summary('d1', 'P6 Paper 2', 'f1'),
      summary('d2', 'P6 Paper 1 Booklet A', 'f1'),
      summary('d3', 'P5 Paper 2'),
    ])
    render(DocumentList)
    await screen.findByRole('link', { name: /P5 Paper 2/ })
    expect(section('Prelims 2026')).toHaveTextContent('2 papers')
    await fireEvent.input(screen.getByRole('searchbox'), { target: { value: 'paper 2' } })
    expect(section('Prelims 2026')).toHaveTextContent('1 match')
    expect(section('Prelims 2026')).not.toHaveTextContent('paper')
    expect(screen.getByRole('status')).toHaveTextContent('2 papers match “paper 2”.')
    await fireEvent.input(screen.getByRole('searchbox'), { target: { value: 'booklet' } })
    expect(screen.getByRole('status')).toHaveTextContent('1 paper matches “booklet”.')
  })

  it('a rename that leaves the search results moves focus to the search box', async () => {
    listDocuments.mockResolvedValue([summary('d1', 'Ratio quiz'), summary('d2', 'Ratio drill')])
    renameDocument.mockResolvedValue({ ...summary('d1', 'Fractions quiz'), version: 4, document: {} })
    render(DocumentList)
    const box = await screen.findByRole('searchbox')
    await fireEvent.input(box, { target: { value: 'ratio' } })
    await choose('Ratio quiz', 'Rename')
    const input = await screen.findByRole('textbox', { name: 'Paper title' })
    await fireEvent.input(input, { target: { value: 'Fractions quiz' } })
    await fireEvent.submit(input.closest('form')!)
    await waitFor(() => expect(screen.queryByRole('link', { name: /Fractions quiz/ })).toBeNull())
    await waitFor(() => expect(box).toHaveFocus())
    expect(screen.getByRole('status')).toHaveTextContent('Renamed to “Fractions quiz”. It no longer matches the search.')
  })

  it('keeps the search box while a search is on, even when no paper is left', async () => {
    listDocuments.mockResolvedValue([summary('d1', 'Ratio quiz')])
    deleteDocument.mockResolvedValue(undefined)
    render(DocumentList)
    await fireEvent.input(await screen.findByRole('searchbox'), { target: { value: 'ratio' } })
    await choose('Ratio quiz', 'Delete…')
    await fireEvent.click(within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Delete paper' }))
    await waitFor(() => expect(screen.queryByRole('link', { name: /Ratio quiz/ })).toBeNull())
    const box = screen.getByRole('searchbox')
    await fireEvent.keyDown(box, { key: 'Escape' })
    // cleared, and with no papers the box goes
    expect(screen.queryByRole('searchbox')).toBeNull()
    expect(screen.getByText(/No papers yet/)).toBeInTheDocument()
  })
})

describe('DocumentList folders (O2, EXA-166)', () => {
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
    const headings = screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent?.trim())
    expect(headings).toEqual(['Term 1', 'Prelims 2026', 'Unfiled'])
    expect(within(section('Prelims 2026')).getByRole('link', { name: /P6 Paper 2/ })).toBeInTheDocument()
    expect(within(section('Term 1')).getByRole('link', { name: /Ratio quiz/ })).toBeInTheDocument()
    const unfiled = within(section('Unfiled'))
    expect(unfiled.getByRole('link', { name: /Fractions drill/ })).toBeInTheDocument()
    // A paper whose folder no longer exists is shown as unfiled.
    expect(unfiled.getByRole('link', { name: /Old copy/ })).toBeInTheDocument()
  })

  it('collapses a folder and remembers it for the next visit', async () => {
    listFolders.mockResolvedValue([folder('f1', 'Prelims 2026')])
    listDocuments.mockResolvedValue([summary('d1', 'P6 Paper 2', 'f1')])
    const { unmount } = render(DocumentList)
    const toggle = await screen.findByRole('button', { name: 'Prelims 2026', expanded: true })
    expect(toggle).toHaveAttribute('aria-controls', 'folder-body-f1')
    await fireEvent.click(toggle)
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('link', { name: /P6 Paper 2/ })).toBeNull()
    // the body the toggle controls is still there, hidden
    expect(document.getElementById('folder-body-f1')).toHaveAttribute('hidden')
    expect(section('Prelims 2026')).toHaveTextContent('1 paper')
    expect(JSON.parse(localStorage.getItem('exam.papers.collapsed')!)).toEqual(['f1'])
    unmount()
    render(DocumentList)
    const again = await screen.findByRole('button', { name: 'Prelims 2026' })
    expect(again).toHaveAttribute('aria-expanded', 'false')
    await fireEvent.click(again)
    expect(screen.getByRole('link', { name: /P6 Paper 2/ })).toBeInTheDocument()
    expect(JSON.parse(localStorage.getItem('exam.papers.collapsed')!)).toEqual([])
  })

  it('still collapses, for the visit, when the browser keeps no storage', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('SecurityError')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('SecurityError')
    })
    listFolders.mockResolvedValue([folder('f1', 'Prelims 2026')])
    listDocuments.mockResolvedValue([summary('d1', 'P6 Paper 2', 'f1')])
    render(DocumentList)
    const toggle = await screen.findByRole('button', { name: 'Prelims 2026', expanded: true })
    await fireEvent.click(toggle)
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('link', { name: /P6 Paper 2/ })).toBeNull()
  })

  it('says when a folder is empty', async () => {
    listFolders.mockResolvedValue([folder('f1', 'Term 1')])
    listDocuments.mockResolvedValue([])
    render(DocumentList)
    expect(await screen.findByText(/No papers here yet/)).toBeInTheDocument()
  })

  it('a folder’s ⋯ menu: New paper in folder… files what the wizard makes there', async () => {
    listFolders.mockResolvedValue([folder('f1', 'Prelims 2026')])
    listDocuments.mockResolvedValue([])
    createDocument.mockResolvedValue({ ...summary('t1', 'Paper 2', 'f1'), document: {} })
    render(DocumentList)
    const trigger = await screen.findByRole('button', { name: 'Actions for folder “Prelims 2026”' })
    await fireEvent.click(trigger)
    const menu = await screen.findByRole('menu', { name: 'Prelims 2026' })
    expect(within(menu).getAllByRole('menuitem').map((r) => r.textContent?.trim())).toEqual([
      'New paper in folder…',
      'Rename folder',
      'Delete folder…',
    ])
    await fireEvent.click(within(menu).getByRole('menuitem', { name: 'New paper in folder…' }))
    const dialog = await screen.findByRole('dialog', { name: 'New' })
    expect(dialog).toHaveTextContent('Papers go in Prelims 2026.')
    await fireEvent.click(within(dialog).getByRole('button', { name: 'Single paper' }))
    await fireEvent.click(await screen.findByRole('button', { name: 'Paper 2' }))
    await fireEvent.click(await screen.findByRole('button', { name: 'Start it empty' }))
    await waitFor(() => expect(location.hash).toBe('#/docs/t1'))
    expect(createDocument).toHaveBeenCalledWith(undefined, 'p2', 'f1')
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
    await waitFor(() => expect(screen.getByRole('button', { name: 'Prelims 2026' })).toHaveFocus())
  })

  it('renames a folder inline from its menu', async () => {
    listFolders.mockResolvedValue([folder('f1', 'Prelims')])
    listDocuments.mockResolvedValue([])
    renameFolder.mockResolvedValue(folder('f1', 'Prelims 2026'))
    render(DocumentList)
    await fireEvent.click(await screen.findByRole('button', { name: 'Actions for folder “Prelims”' }))
    await fireEvent.click(await screen.findByRole('menuitem', { name: 'Rename folder' }))
    const input = screen.getByRole('textbox', { name: 'Folder name' })
    expect(input).toHaveValue('Prelims')
    await fireEvent.input(input, { target: { value: 'Prelims 2026' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(renameFolder).toHaveBeenCalledWith('f1', 'Prelims 2026'))
    expect(await screen.findByRole('heading', { name: 'Prelims 2026' })).toBeInTheDocument()
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Actions for folder “Prelims 2026”' })).toHaveFocus(),
    )
  })

  it('keeps the rename field open and shows the error when the rename fails', async () => {
    listFolders.mockResolvedValue([folder('f1', 'Prelims')])
    listDocuments.mockResolvedValue([])
    renameFolder.mockRejectedValue(new ApiError(422, 'name must be 1-80 characters'))
    render(DocumentList)
    await fireEvent.click(await screen.findByRole('button', { name: 'Actions for folder “Prelims”' }))
    await fireEvent.click(await screen.findByRole('menuitem', { name: 'Rename folder' }))
    await fireEvent.input(screen.getByRole('textbox', { name: 'Folder name' }), { target: { value: 'X' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByRole('alert')).toHaveTextContent("The folder wasn't renamed. Name must be 1-80 characters.")
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
    const openDelete = async () => {
      await fireEvent.click(await screen.findByRole('button', { name: 'Actions for folder “Prelims 2026”' }))
      await fireEvent.click(await screen.findByRole('menuitem', { name: 'Delete folder…' }))
      return screen.findByRole('alertdialog', { name: 'Delete the folder “Prelims 2026”?' })
    }
    let dialog = await openDelete()
    expect(dialog).toHaveTextContent('Its 2 papers will move to Unfiled. No paper is deleted.')
    await fireEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }))
    expect(screen.queryByRole('alertdialog')).toBeNull()
    expect(deleteFolder).not.toHaveBeenCalled()
    dialog = await openDelete()
    await fireEvent.click(within(dialog).getByRole('button', { name: 'Delete folder' }))
    await waitFor(() => expect(deleteFolder).toHaveBeenCalledWith('f1'))
    await waitFor(() => expect(screen.queryByRole('heading', { name: 'Prelims 2026' })).toBeNull())
    // No folders left: the papers are listed (unfiled), none deleted.
    expect(screen.getByRole('link', { name: /P6 Paper 2/ })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /P6 Paper 1 Booklet A/ })).toBeInTheDocument()
    expect(deleteDocument).not.toHaveBeenCalled()
    expect(screen.getByRole('status')).toHaveTextContent('Folder “Prelims 2026” deleted. Its papers are in Unfiled.')
  })
})
