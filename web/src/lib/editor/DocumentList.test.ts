import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/svelte'

const listDocuments = vi.fn()
const createDocument = vi.fn()
const deleteDocument = vi.fn()
vi.mock('./docsApi', () => ({
  listDocuments: (...a: unknown[]) => listDocuments(...a),
  createDocument: (...a: unknown[]) => createDocument(...a),
  deleteDocument: (...a: unknown[]) => deleteDocument(...a),
}))

import DocumentList from './DocumentList.svelte'

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
})
