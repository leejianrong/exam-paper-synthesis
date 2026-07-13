import { describe, it, expect, beforeEach } from 'vitest'
import { get } from 'svelte/store'
import { render, screen, fireEvent } from '@testing-library/svelte'
import WorksheetTray from './WorksheetTray.svelte'
import { worksheet, DEFAULT_TITLE } from './worksheet'
import type { Question } from './types'

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
})
