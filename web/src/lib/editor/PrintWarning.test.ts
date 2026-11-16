import { describe, it, expect, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/svelte'
import PrintWarning from './PrintWarning.svelte'

describe('PrintWarning (EXA-137: empty placeholders never print by accident)', () => {
  it('lists the empty questions and offers Fill them, Print anyway and Cancel', async () => {
    const fill = vi.fn()
    const print = vi.fn()
    const cancel = vi.fn()
    render(PrintWarning, { props: { questions: [9, 10, 12] }, events: { fill, print, cancel } })

    const dialog = screen.getByRole('alertdialog', { name: '3 questions are still empty' })
    expect(dialog).toHaveTextContent('Questions 9, 10 and 12 were left for you to write')
    await fireEvent.click(screen.getByRole('button', { name: 'Fill them' }))
    await fireEvent.click(screen.getByRole('button', { name: 'Print anyway' }))
    await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect([fill, print, cancel].map((f) => f.mock.calls.length)).toEqual([1, 1, 1])
  })

  it('speaks of one question in the singular', () => {
    render(PrintWarning, { props: { questions: [4] } })
    expect(screen.getByRole('alertdialog', { name: 'A question is still empty' })).toHaveTextContent(
      'Question 4 was left for you to write',
    )
    expect(screen.getByRole('button', { name: 'Fill it' })).toBeInTheDocument()
  })
})
