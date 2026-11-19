import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/svelte'
import EditorBar from './EditorBar.svelte'
import { session } from '../session'

beforeEach(() => session.set({ status: 'user', user: { id: 'local', email: null, name: 'Local', dev: true } }))

function setup(props: Record<string, unknown> = {}) {
  const onExport = vi.fn()
  const onPreview = vi.fn()
  const onRename = vi.fn()
  render(EditorBar, {
    props: {
      title: 'P6 Paper 2',
      folderName: 'P6 Prelims 2026',
      status: 'saved',
      marks: 55,
      target: 55,
      hasQuestions: true,
      onExport,
      onPreview,
      onRename,
      ...props,
    },
  })
  return { onExport, onPreview, onRename }
}

describe('EditorBar (EXA-160)', () => {
  it('shows the folder / title breadcrumb, the save state and the marks in neutral ink', () => {
    setup()
    expect(screen.getByText('P6 Prelims 2026 /')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'P6 Paper 2' })).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Saved')
    const total = screen.getByTestId('marks-total')
    expect(total).toHaveTextContent(/55 \/ 55 marks/)
    expect(total).not.toHaveClass('off')
    expect(total.querySelector('svg')).toBeNull()
  })

  it('turns the total red with an icon and a reason only when a section is off target', () => {
    setup({ marks: 57, offTarget: 'Section B: 47 of 45 marks' })
    const total = screen.getByTestId('marks-total')
    expect(total).toHaveClass('off')
    expect(total.querySelector('svg')).not.toBeNull()
    expect(total).toHaveTextContent('Section B: 47 of 45 marks')
  })

  it('has no target to show when sections have none', () => {
    setup({ target: null, marks: 12 })
    expect(screen.getByTestId('marks-total')).toHaveTextContent(/^\s*12 marks\s*$/)
  })

  it('Export is one menu: the three PDFs and the allowance as a footer', async () => {
    const { onExport } = setup({ quota: { per_day: 30, left_day: 24 } })
    const exportButton = screen.getByRole('button', { name: 'Export' })
    expect(exportButton).toHaveClass('primary')
    await fireEvent.click(exportButton)
    const names = screen.getAllByRole('menuitem').map((m) => m.textContent?.trim())
    expect(names).toEqual(['Student paper (PDF)', 'Answer key (PDF)', 'Paper and key together (PDF)'])
    expect(screen.getByText('24 exports left today')).toBeInTheDocument()
    await fireEvent.click(screen.getByRole('menuitem', { name: 'Paper and key together (PDF)' }))
    expect(onExport).toHaveBeenCalledWith('full')
  })

  it('the answer key cannot be exported from an empty paper, and says why', async () => {
    setup({ hasQuestions: false })
    await fireEvent.click(screen.getByRole('button', { name: 'Export' }))
    const key = screen.getByRole('menuitem', { name: 'Answer key (PDF)' })
    expect(key).toHaveAttribute('aria-disabled', 'true')
    expect(key.title).toMatch(/Add a question first/)
  })

  it('Preview is a secondary button; the title button asks to rename', async () => {
    const { onPreview, onRename } = setup()
    const preview = screen.getByRole('button', { name: 'Preview' })
    expect(preview).not.toHaveClass('primary')
    await fireEvent.click(preview)
    expect(onPreview).toHaveBeenCalled()
    await fireEvent.click(screen.getByRole('button', { name: 'P6 Paper 2' }))
    expect(onRename).toHaveBeenCalled()
  })

  it('locks Preview and Export while something is running', () => {
    setup({ busy: 'export-student' })
    expect(screen.getByRole('button', { name: 'Preview' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Exporting…' })).toBeDisabled()
  })

  it('carries the account avatar and a labelled back link', () => {
    setup()
    expect(screen.getByRole('button', { name: 'Account: Local' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to papers' })).toHaveAttribute('href', '#/')
  })
})
