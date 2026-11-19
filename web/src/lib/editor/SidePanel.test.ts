import { describe, it, expect } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/svelte'
import SidePanel from './SidePanel.svelte'
import { freeformDocNode, makeQuestion, templatedNodes } from './fixtures'

const blocks = () => [...templatedNodes([makeQuestion()]), freeformDocNode({ id: 'ff_9', marks: 2 })]
const sections = [
  { title: 'Section A', marks: 10, target: 10 },
  { title: 'Section B', marks: 47, target: 45 },
]

describe('SidePanel (EXA-160)', () => {
  it('opens on the Paper tab: marks per section, the question count and the layout fields', () => {
    render(SidePanel, { props: { blocks: blocks(), marks: 57, sections } })
    expect(screen.getByRole('tab', { name: 'Paper' })).toHaveAttribute('aria-selected', 'true')
    const panel = screen.getByRole('tabpanel', { name: 'Paper' })
    expect(panel).toHaveTextContent(/Section A\s*10 \/ 10/)
    expect(panel).toHaveTextContent(/Section B\s*47 \/ 45/)
    expect(panel).toHaveTextContent('over target')
    expect(panel).toHaveTextContent(/Questions\s*2/)
    expect(screen.getByLabelText('Paper time in minutes')).toBeInTheDocument()
    expect(screen.getByLabelText('First question number')).toBeInTheDocument()
    expect(screen.getByLabelText('Marks shown')).toBeInTheDocument()
  })

  it('selecting a question brings its tab forward, named by its number', async () => {
    const view = render(SidePanel, { props: { blocks: blocks(), marks: 5, selectedId: null, start: 16 } })
    expect(screen.getByRole('tab', { name: 'Question' })).toHaveAttribute('aria-selected', 'false')
    await view.rerender({ blocks: blocks(), marks: 5, selectedId: 'ff_9', start: 16 })
    const tab = screen.getByRole('tab', { name: 'Question 17' })
    expect(tab).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tabpanel', { name: 'Question 17' })).toHaveTextContent('Question 17')
    // going back to Paper sticks while the same question stays selected
    await fireEvent.click(screen.getByRole('tab', { name: 'Paper' }))
    await view.rerender({ blocks: blocks(), marks: 6, selectedId: 'ff_9', start: 16 })
    expect(screen.getByRole('tab', { name: 'Paper' })).toHaveAttribute('aria-selected', 'true')
  })

  it('arrow keys move between the tabs', async () => {
    render(SidePanel, { props: { blocks: blocks(), marks: 5 } })
    const paper = screen.getByRole('tab', { name: 'Paper' })
    paper.focus()
    await fireEvent.keyDown(paper, { key: 'ArrowRight' })
    const question = screen.getByRole('tab', { name: 'Question' })
    expect(question).toHaveAttribute('aria-selected', 'true')
    expect(question).toHaveFocus()
    expect(question).toHaveAttribute('tabindex', '0')
    expect(paper).toHaveAttribute('tabindex', '-1')
  })

  it('on a generated paper: the lock count, placeholders left, and Regenerate with its count', async () => {
    const seen: string[] = []
    render(SidePanel, {
      props: { blocks: blocks(), marks: 5, regen: { unlocked: 15, locked: 2 }, placeholdersLeft: 1 },
      events: { regenerate: () => seen.push('regen') },
    })
    expect(screen.getByText('2 of 17')).toBeInTheDocument()
    expect(screen.getByTestId('placeholders-left')).toHaveTextContent('1 placeholder to write')
    await fireEvent.click(screen.getByRole('button', { name: 'Regenerate 15 unlocked…' }))
    expect(seen).toEqual(['regen'])
  })

  it('has no Generated paper group on a paper with nothing generated', () => {
    render(SidePanel, { props: { blocks: blocks(), marks: 5, regen: null } })
    expect(screen.queryByText('Generated paper')).toBeNull()
  })
})
