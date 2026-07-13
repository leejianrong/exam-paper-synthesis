import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { get } from 'svelte/store'
import { render, screen, fireEvent } from '@testing-library/svelte'
import WorksheetTray from './WorksheetTray.svelte'
import { worksheet, DEFAULT_TITLE } from './worksheet'
import { previewWorksheet, exportPdf } from './api'
import type { Question } from './types'

// Stub the export API so the tray's buttons can be exercised without a network.
vi.mock('./api', () => ({
  previewWorksheet: vi.fn(async () => '<main class="sheet worksheet"></main>'),
  exportPdf: vi.fn(async () => new Blob(['%PDF'], { type: 'application/pdf' })),
}))

// Minimal canonical objects — only the fields the tray reads.
function q(id: string, text: string, marks: number): Question {
  return {
    id,
    seed: 1,
    blueprint_code: 'ratio_medium',
    validation: { status: 'pass' },
    question: { parts: [{ text, marks }], total_marks: marks },
  }
}

const ids = () => get(worksheet).items.map((item) => item.id)

describe('WorksheetTray', () => {
  beforeEach(() => {
    worksheet.clear()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('shows the empty state when there are no items', () => {
    render(WorksheetTray)
    expect(screen.getByText(/No questions yet/i)).toBeInTheDocument()
    // No total-marks line while empty.
    expect(screen.queryByText(/Total marks/i)).not.toBeInTheDocument()
  })

  it('renders each item with its label, marks, and the running total', () => {
    worksheet.add(q('a', 'Anna and Ben share $90 in the ratio 2 : 3.', 2))
    worksheet.add(q('b', 'A tank holds 12 litres of water.', 3))
    render(WorksheetTray)

    expect(screen.getByText(/Anna and Ben share/)).toBeInTheDocument()
    expect(screen.getByText(/A tank holds/)).toBeInTheDocument()
    // Per-item marks + the summed total (2 + 3 = 5).
    expect(screen.getByText('[2]')).toBeInTheDocument()
    expect(screen.getByText('[3]')).toBeInTheDocument()
    expect(screen.getByText(/Total marks/i)).toBeInTheDocument()
    expect(screen.getByText('[5]')).toBeInTheDocument()
  })

  it('removes an item from the store when its remove button is clicked', async () => {
    worksheet.add(q('a', 'First question', 2))
    worksheet.add(q('b', 'Second question', 3))
    render(WorksheetTray)

    const removeButtons = screen.getAllByRole('button', { name: 'Remove' })
    await fireEvent.click(removeButtons[0])

    expect(ids()).toEqual(['b'])
  })

  it('reorders items via the up/down buttons', async () => {
    worksheet.add(q('a', 'First question', 2))
    worksheet.add(q('b', 'Second question', 3))
    render(WorksheetTray)

    // Move the second item up.
    const upButtons = screen.getAllByRole('button', { name: 'Move up' })
    await fireEvent.click(upButtons[1])
    expect(ids()).toEqual(['b', 'a'])

    // Move it back down.
    const downButtons = screen.getAllByRole('button', { name: 'Move down' })
    await fireEvent.click(downButtons[0])
    expect(ids()).toEqual(['a', 'b'])
  })

  it('disables up on the first item and down on the last', () => {
    worksheet.add(q('a', 'First question', 2))
    worksheet.add(q('b', 'Second question', 3))
    render(WorksheetTray)

    const upButtons = screen.getAllByRole('button', { name: 'Move up' })
    const downButtons = screen.getAllByRole('button', { name: 'Move down' })
    expect(upButtons[0]).toBeDisabled()
    expect(upButtons[1]).not.toBeDisabled()
    expect(downButtons[0]).not.toBeDisabled()
    expect(downButtons[1]).toBeDisabled()
  })

  it('updates the store title when the title input is edited', async () => {
    render(WorksheetTray)
    const input = screen.getByRole('textbox') as HTMLInputElement
    expect(input.value).toBe(DEFAULT_TITLE)

    await fireEvent.input(input, { target: { value: 'Term 3 Ratio' } })
    expect(get(worksheet).title).toBe('Term 3 Ratio')
  })

  describe('export actions', () => {
    const previewBtn = () => screen.getByRole('button', { name: /^Preview$/i })
    const worksheetBtn = () => screen.getByRole('button', { name: /Export worksheet PDF/i })
    const answerKeyBtn = () => screen.getByRole('button', { name: /Export answer-key PDF/i })

    beforeEach(() => {
      // The download path touches URL object URLs + window.open; stub them so
      // the handlers run cleanly under jsdom.
      Object.assign(URL, {
        createObjectURL: vi.fn(() => 'blob:mock'),
        revokeObjectURL: vi.fn(),
      })
      vi.stubGlobal('open', vi.fn())
      // The synthetic <a download> click would trigger a jsdom "navigation not
      // implemented" warning; no-op it (real browsers handle the download).
      vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    })

    afterEach(() => {
      vi.unstubAllGlobals()
      vi.restoreAllMocks()
    })

    it('disables all three export buttons while the worksheet is empty', () => {
      render(WorksheetTray)
      expect(previewBtn()).toBeDisabled()
      expect(worksheetBtn()).toBeDisabled()
      expect(answerKeyBtn()).toBeDisabled()
    })

    it('enables the export buttons once the worksheet has items', () => {
      worksheet.add(q('a', 'First question', 2))
      render(WorksheetTray)
      expect(previewBtn()).not.toBeDisabled()
      expect(worksheetBtn()).not.toBeDisabled()
      expect(answerKeyBtn()).not.toBeDisabled()
    })

    it('Preview calls previewWorksheet with the store title + items', async () => {
      worksheet.setTitle('Term 3 Ratio')
      const item = q('a', 'First question', 2)
      worksheet.add(item)
      render(WorksheetTray)

      await fireEvent.click(previewBtn())

      expect(previewWorksheet).toHaveBeenCalledTimes(1)
      expect(previewWorksheet).toHaveBeenCalledWith('Term 3 Ratio', [item])
    })

    it('Export worksheet PDF calls exportPdf("worksheet", …) with the store contents', async () => {
      worksheet.setTitle('Term 3 Ratio')
      const item = q('a', 'First question', 2)
      worksheet.add(item)
      render(WorksheetTray)

      await fireEvent.click(worksheetBtn())

      expect(exportPdf).toHaveBeenCalledTimes(1)
      expect(exportPdf).toHaveBeenCalledWith('worksheet', 'Term 3 Ratio', [item])
    })

    it('Export answer-key PDF calls exportPdf("answer-key", …) with the store contents', async () => {
      worksheet.setTitle('Term 3 Ratio')
      const item = q('a', 'First question', 2)
      worksheet.add(item)
      render(WorksheetTray)

      await fireEvent.click(answerKeyBtn())

      expect(exportPdf).toHaveBeenCalledTimes(1)
      expect(exportPdf).toHaveBeenCalledWith('answer-key', 'Term 3 Ratio', [item])
    })

    it('surfaces an error message when an export fails', async () => {
      vi.mocked(exportPdf).mockRejectedValueOnce(new Error('API 422: no questions to export'))
      worksheet.add(q('a', 'First question', 2))
      render(WorksheetTray)

      await fireEvent.click(worksheetBtn())

      expect(await screen.findByRole('alert')).toHaveTextContent('API 422: no questions to export')
    })
  })
})
