import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/svelte'

const listDocuments = vi.fn()
const createDocument = vi.fn()
const deleteDocument = vi.fn()
const listPaperTemplates = vi.fn()
const generatePaper = vi.fn()
vi.mock('./docsApi', () => ({
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
import { get } from 'svelte/store'
import { lastReport } from './paperReport'
import { settings } from '../settings'

const summary = (id: string, title: string) => ({
  id,
  title,
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

  it('creates a paper and navigates into it', async () => {
    listDocuments.mockResolvedValue([])
    createDocument.mockResolvedValue({ ...summary('new1', 'Untitled paper'), document: {} })
    render(DocumentList)
    await fireEvent.click(await screen.findByRole('button', { name: '+ New paper' }))
    await waitFor(() => expect(location.hash).toBe('#/docs/new1'))
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

  it('starts a paper from an engine template by its code', async () => {
    listDocuments.mockResolvedValue([])
    createDocument.mockResolvedValue({ ...summary('t1', 'Paper 2'), document: {} })
    render(DocumentList)
    await fireEvent.click(await screen.findByRole('button', { name: 'Paper 2' }))
    await waitFor(() => expect(location.hash).toBe('#/docs/t1'))
    expect(createDocument).toHaveBeenCalledWith(undefined, 'p2')
  })

  it('generates a whole paper for the chosen template and level, and hands on the report', async () => {
    listDocuments.mockResolvedValue([])
    const report = { template: 'p1_booklet_b', level: 'P5', filled: 7, placeholders: 8 }
    generatePaper.mockResolvedValue({ ...summary('g1', 'P5 Paper 1 Booklet B'), document: {}, report })
    render(DocumentList)
    const form = await screen.findByRole('form', { name: 'Generate a paper' })
    expect(form).toBeInTheDocument()
    // Paper 2 is preselected (the last template); pick Booklet B at P5
    await waitFor(() => expect(screen.getByLabelText('Paper to generate')).toHaveValue('p2'))
    await fireEvent.change(screen.getByLabelText('Paper to generate'), { target: { value: 'p1_booklet_b' } })
    await fireEvent.change(screen.getByLabelText('Level'), { target: { value: 'P5' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Generate paper' }))
    await waitFor(() => expect(location.hash).toBe('#/docs/g1'))
    expect(generatePaper).toHaveBeenCalledWith('p1_booklet_b', 'P5')
    expect(get(lastReport)).toEqual({ docId: 'g1', report })
  })

  it('hides the Classic generator link unless the setting is on (O1); Settings is always there', async () => {
    listDocuments.mockResolvedValue([])
    settings.set({ classic_generator: false })
    const { unmount } = render(DocumentList)
    expect(await screen.findByRole('link', { name: 'Settings' })).toHaveAttribute('href', '#/settings')
    expect(screen.queryByRole('link', { name: 'Classic generator' })).toBeNull()
    unmount()
    settings.set({ classic_generator: true })
    render(DocumentList)
    expect(await screen.findByRole('link', { name: 'Classic generator' })).toHaveAttribute('href', '#/classic')
  })
})
