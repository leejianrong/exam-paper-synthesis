import { ApiError } from '../errors'
import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/svelte'
import { get } from 'svelte/store'

const createDocument = vi.fn()
const createFolder = vi.fn()
const generatePaper = vi.fn()
vi.mock('./docsApi', () => ({
  createDocument: (...a: unknown[]) => createDocument(...a),
  createFolder: (...a: unknown[]) => createFolder(...a),
  generatePaper: (...a: unknown[]) => generatePaper(...a),
}))

import NewWizard from './NewWizard.svelte'
import { lastReport } from './paperReport'

const tpl = (code: string, label: string, time_min = 60) => ({
  code,
  label,
  title: label,
  time_min,
  sections: [{ title: 'Section A', mode: 'short', marks_target: 20, questions: 10 }],
})
const TEMPLATES = [
  tpl('p1_booklet_a', 'Paper 1 · Booklet A'),
  tpl('p1_booklet_b', 'Paper 1 · Booklet B'),
  tpl('p2', 'Paper 2', 90),
]
const folder = (id: string, name: string) => ({ id, name, created_at: '', updated_at: '' })
const record = (id: string, folder_id: string | null = null) => ({
  id,
  title: id,
  folder_id,
  total_marks: 0,
  version: 1,
  created_at: '',
  updated_at: '',
  document: {},
})

let props: {
  onClose: Mock<() => void>
  onFolderCreated: Mock<(f: unknown) => void>
  onPapersCreated: Mock<(docs: unknown[]) => void>
  onShowFolder: Mock<(id: string) => void>
}

function open(extra: Record<string, unknown> = {}) {
  props = {
    onClose: vi.fn(),
    onFolderCreated: vi.fn(),
    onPapersCreated: vi.fn(),
    onShowFolder: vi.fn(),
  }
  render(NewWizard, {
    props: { folders: [folder('f1', 'Prelims 2026')], templates: TEMPLATES, levels: ['P5', 'P6'], ...props, ...extra },
  })
  return screen.getByRole('dialog')
}

const pick = (name: string) => fireEvent.click(screen.getByRole('button', { name }))

beforeEach(() => {
  for (const m of [createDocument, createFolder, generatePaper]) m.mockReset()
  lastReport.set(null)
  location.hash = ''
})

describe('NewWizard: the first step', () => {
  it('offers the four choices in order, exam set first and focused (EXA-166)', async () => {
    open()
    const group = screen.getByRole('group', { name: 'What to make' })
    const cards = within(group).getAllByRole('button')
    const names = ['Exam set', 'Single paper', 'Blank paper', 'New folder']
    names.forEach((n, i) => expect(cards[i]).toBe(screen.getByRole('button', { name: n })))
    expect(screen.getByRole('button', { name: 'Exam set' })).toHaveAccessibleDescription(
      'Paper 1 Booklet A, Booklet B and Paper 2 in one folder.',
    )
    await waitFor(() => expect(cards[0]).toHaveFocus())
  })

  it('arrow keys move between the cards, Home/End jump, and Enter picks one', async () => {
    const dialog = open()
    const cards = within(screen.getByRole('group', { name: 'What to make' })).getAllByRole('button')
    await waitFor(() => expect(cards[0]).toHaveFocus())
    await fireEvent.keyDown(cards[0], { key: 'ArrowDown' })
    expect(cards[1]).toHaveFocus()
    await fireEvent.keyDown(cards[1], { key: 'ArrowUp' })
    await fireEvent.keyDown(cards[0], { key: 'ArrowUp' })
    expect(cards[3]).toHaveFocus() // wraps
    await fireEvent.keyDown(cards[3], { key: 'Home' })
    expect(cards[0]).toHaveFocus()
    await fireEvent.keyDown(cards[0], { key: 'End' })
    expect(cards[3]).toHaveFocus()
    await fireEvent.keyDown(cards[3], { key: 'ArrowLeft' })
    await fireEvent.keyDown(cards[2], { key: 'ArrowLeft' })
    // A native button turns Enter into a click.
    await fireEvent.click(document.activeElement as HTMLElement)
    expect(within(dialog).getByRole('heading')).toHaveTextContent('Single paper')
  })

  it('Escape on the first step closes; Tab and Shift+Tab stay in the dialog', async () => {
    const dialog = open()
    const cards = within(screen.getByRole('group', { name: 'What to make' })).getAllByRole('button')
    const close = screen.getByRole('button', { name: 'Close' })
    // Close (in the header) is first, the last card is last: Tab wraps both ways.
    await waitFor(() => expect(cards[0]).toHaveFocus())
    cards[3].focus()
    await fireEvent.keyDown(cards[3], { key: 'Tab' })
    expect(close).toHaveFocus()
    await fireEvent.keyDown(close, { key: 'Tab', shiftKey: true })
    expect(cards[3]).toHaveFocus()
    expect(props.onClose).not.toHaveBeenCalled()
    await fireEvent.keyDown(dialog, { key: 'Escape' })
    expect(props.onClose).toHaveBeenCalledTimes(1)
  })

  it('Blank paper opens in the editor, filed in the folder it was opened from', async () => {
    createDocument.mockResolvedValue(record('b1', 'f1'))
    open({ contextFolder: folder('f1', 'Prelims 2026') })
    expect(screen.getByRole('dialog')).toHaveTextContent('Papers go in Prelims 2026.')
    await pick('Blank paper')
    await waitFor(() => expect(location.hash).toBe('#/docs/b1'))
    expect(createDocument).toHaveBeenCalledWith(undefined, undefined, 'f1')
    expect(props.onClose).toHaveBeenCalled()
  })

  it('shows an error and stays open when making the paper fails', async () => {
    createDocument.mockRejectedValue(new ApiError(500, 'boom'))
    open()
    await pick('Blank paper')
    expect(await screen.findByRole('alert')).toHaveTextContent(
      "The paper wasn't made. Something went wrong on our side. Try again in a moment. Check Your papers before trying again.",
    )
    expect(props.onClose).not.toHaveBeenCalled()
    expect(location.hash).toBe('')
  })
})

describe('NewWizard: New folder', () => {
  it('names the folder, creates it and shows it; Back and Escape return to the choices', async () => {
    createFolder.mockResolvedValue(folder('f9', 'Term 4'))
    const dialog = open()
    await pick('New folder')
    expect(within(dialog).getByRole('heading')).toHaveTextContent('New folder')
    const input = screen.getByRole('textbox', { name: 'Folder name' })
    await waitFor(() => expect(input).toHaveFocus())
    await fireEvent.keyDown(input, { key: 'Escape' })
    expect(within(dialog).getByRole('heading')).toHaveTextContent('New')
    await waitFor(() => expect(screen.getByRole('button', { name: 'New folder' })).toHaveFocus())
    expect(props.onClose).not.toHaveBeenCalled()
    await pick('New folder')
    await pick('Back')
    expect(screen.getByRole('group', { name: 'What to make' })).toBeInTheDocument()
    await pick('New folder')
    expect(screen.getByRole('button', { name: 'Create folder' })).toBeDisabled()
    await fireEvent.input(screen.getByRole('textbox', { name: 'Folder name' }), { target: { value: ' Term 4 ' } })
    await pick('Create folder')
    await waitFor(() => expect(props.onShowFolder).toHaveBeenCalledWith('f9'))
    expect(createFolder).toHaveBeenCalledWith('Term 4')
    expect(props.onFolderCreated).toHaveBeenCalledWith(folder('f9', 'Term 4'))
  })
})

describe('NewWizard: Exam set', () => {
  const TOPICS: Record<string, Record<string, number>> = {
    p1_booklet_a: { Ratio: 2, Rate: 1 },
    p1_booklet_b: { Ratio: 1, Volume: 2 },
    p2: { Speed: 4 },
  }

  it('generates the three papers at a level into a new folder, one at a time, then shows it', async () => {
    createFolder.mockResolvedValue(folder('fs', 'P5 mocks'))
    generatePaper.mockImplementation(async (code: string, _level: string, fid: string) => ({
      ...record(`g-${code}`, fid),
      report: { topics: TOPICS[code] },
    }))
    open()
    await pick('Exam set')
    expect(screen.getByRole('radio', { name: 'A new folder' })).toBeChecked()
    const name = screen.getByRole('textbox', { name: 'Folder name' })
    expect(name).toHaveValue('P6 exam set')
    await fireEvent.input(name, { target: { value: 'P5 mocks' } })
    await pick('Next')
    expect(screen.getByRole('dialog')).toHaveTextContent('Into the new folder P5 mocks.')
    await pick('Generate at P5')
    await waitFor(() => expect(props.onShowFolder).toHaveBeenCalledWith('fs'))
    expect(createFolder).toHaveBeenCalledWith('P5 mocks')
    // EXA-153: filled Paper 2 first, each paper told the topics of the set's papers made before it
    expect(generatePaper.mock.calls).toEqual([
      ['p2', 'P5', 'fs', {}],
      ['p1_booklet_b', 'P5', 'fs', { Speed: 4 }],
      ['p1_booklet_a', 'P5', 'fs', { Speed: 4, Ratio: 1, Volume: 2 }],
    ])
    // the progress list keeps the printed order
    const rows = within(screen.getByRole('list', { name: 'Exam set papers' })).getAllByRole('listitem')
    expect(rows.map((r) => r.textContent)).toEqual([
      expect.stringContaining('Booklet A'),
      expect.stringContaining('Booklet B'),
      expect.stringContaining('Paper 2'),
    ])
    expect(props.onPapersCreated).toHaveBeenCalledTimes(3)
    expect(props.onPapersCreated.mock.calls[0][0][0]).not.toHaveProperty('document')
    expect(createDocument).not.toHaveBeenCalled()
  })

  it('makes empty starters into an existing folder (the one it was opened from)', async () => {
    createDocument.mockImplementation(async (_t: unknown, code: string, fid: string) => record(`e-${code}`, fid))
    open({ contextFolder: folder('f1', 'Prelims 2026') })
    await pick('Exam set')
    expect(screen.getByRole('radio', { name: 'Prelims 2026' })).toBeChecked()
    expect(screen.queryByRole('textbox', { name: 'Folder name' })).toBeNull()
    await pick('Next')
    await pick('Empty starters')
    await waitFor(() => expect(props.onShowFolder).toHaveBeenCalledWith('f1'))
    expect(createFolder).not.toHaveBeenCalled()
    expect(createDocument.mock.calls).toEqual([
      [undefined, 'p1_booklet_a', 'f1'],
      [undefined, 'p1_booklet_b', 'f1'],
      [undefined, 'p2', 'f1'],
    ])
  })

  it('on a partial failure says which paper failed, keeps the others, and can try it again', async () => {
    createFolder.mockResolvedValue(folder('fs', 'P6 exam set'))
    generatePaper.mockImplementation(async (code: string, _l: string, fid: string) => {
      if (code === 'p1_booklet_b') throw new ApiError(503, 'try later')
      return { ...record(`g-${code}`, fid), report: { topics: TOPICS[code] } }
    })
    open()
    await pick('Exam set')
    await pick('Next')
    await pick('Generate at P6')
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Booklet B could not be made. Booklet A and Paper 2 are in P6 exam set.')
    expect(alert).toHaveTextContent('Booklet B: The server is busy. Try again in a moment.')
    const rows = within(screen.getByRole('list', { name: 'Exam set papers' })).getAllByRole('listitem')
    expect(rows.map((r) => r.className.split(' ')[0])).toEqual(['done', 'failed', 'done'])
    expect(props.onPapersCreated).toHaveBeenCalledTimes(2)
    expect(props.onShowFolder).not.toHaveBeenCalled()
    // No Back once papers exist; Escape closes (what was made stays).
    expect(screen.queryByRole('button', { name: 'Back' })).toBeNull()

    generatePaper.mockImplementation(async (code: string, _l: string, fid: string) => record(`g-${code}`, fid))
    await pick('Try Booklet B again')
    await waitFor(() => expect(props.onShowFolder).toHaveBeenCalledWith('fs'))
    expect(generatePaper.mock.calls.filter((c) => c[0] === 'p1_booklet_b')).toHaveLength(2)
    // the retried paper is told the topics of both papers already made
    expect(generatePaper.mock.calls.at(-1)).toEqual(['p1_booklet_b', 'P6', 'fs', { Ratio: 2, Rate: 1, Speed: 4 }])
    expect(generatePaper.mock.calls.filter((c) => c[0] === 'p1_booklet_a')).toHaveLength(1)
    expect(createFolder).toHaveBeenCalledTimes(1)
  })

  it('after a failure, Show the folder and Escape both leave with what was made', async () => {
    createFolder.mockResolvedValue(folder('fs', 'P6 exam set'))
    createDocument.mockRejectedValue(new ApiError(500, 'down'))
    const dialog = open()
    await pick('Exam set')
    await pick('Next')
    await pick('Empty starters')
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Booklet A and Booklet B and Paper 2 could not be made.',
    )
    await pick('Show the folder')
    expect(props.onShowFolder).toHaveBeenCalledWith('fs')
    await fireEvent.keyDown(dialog, { key: 'Escape' })
    expect(props.onClose).toHaveBeenCalled()
  })

  it('if the folder cannot be made, no paper is attempted and the step stays', async () => {
    createFolder.mockRejectedValue(new ApiError(422, 'name must be 1-80 characters'))
    open()
    await pick('Exam set')
    await pick('Next')
    await pick('Empty starters')
    expect(await screen.findByRole('alert')).toHaveTextContent("The folder wasn't made, so no paper was. Name must be 1-80 characters.")
    expect(createDocument).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Empty starters' })).toBeInTheDocument()
  })

  it('Escape and Back step back through the exam set', async () => {
    const dialog = open()
    await pick('Exam set')
    await pick('Next')
    await fireEvent.keyDown(screen.getByRole('button', { name: 'Empty starters' }), { key: 'Escape' })
    expect(screen.getByRole('button', { name: 'Next' })).toBeInTheDocument()
    await pick('Back')
    expect(screen.getByRole('group', { name: 'What to make' })).toBeInTheDocument()
    expect(within(dialog).queryByRole('button', { name: 'Back' })).toBeNull()
    expect(props.onClose).not.toHaveBeenCalled()
  })
})

describe('NewWizard: Single paper', () => {
  it('generates the chosen paper at a level into the chosen folder, with the report', async () => {
    const report = { template: 'p1_booklet_b', level: 'P6', filled: 13 }
    generatePaper.mockResolvedValue({ ...record('s1', 'f1'), report })
    open()
    await pick('Single paper')
    const papers = within(screen.getByRole('group', { name: 'Which paper' })).getAllByRole('button')
    expect(papers.map((b) => b.getAttribute('aria-labelledby'))).toEqual([
      'nw-sl-p1_booklet_a',
      'nw-sl-p1_booklet_b',
      'nw-sl-p2',
    ])
    expect(screen.getByRole('button', { name: 'Paper 2' })).toHaveAccessibleDescription(
      '1 section · 10 questions · 20 marks · 1 h 30 min',
    )
    await pick('Paper 1 · Booklet B')
    const where = screen.getByRole('combobox', { name: 'Folder (optional)' })
    expect(where).toHaveValue('')
    await fireEvent.change(where, { target: { value: 'f1' } })
    await pick('Generate at P6')
    await waitFor(() => expect(location.hash).toBe('#/docs/s1'))
    expect(generatePaper).toHaveBeenCalledWith('p1_booklet_b', 'P6', 'f1')
    expect(get(lastReport)).toEqual({ docId: 's1', report })
  })

  it('starts a single paper empty, unfiled by default', async () => {
    createDocument.mockResolvedValue(record('s2'))
    open()
    await pick('Single paper')
    await pick('Paper 2')
    await pick('Start it empty')
    await waitFor(() => expect(location.hash).toBe('#/docs/s2'))
    expect(createDocument).toHaveBeenCalledWith(undefined, 'p2', null)
  })

})
