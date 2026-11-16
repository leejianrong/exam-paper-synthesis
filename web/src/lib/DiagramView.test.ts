import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/svelte'
import DiagramView from './DiagramView.svelte'
import type { DiagramSpec } from './diagram'

describe('DiagramView worked-model note (EXA-132)', () => {
  it('labels a bar model as key-only: the student paper never prints it', () => {
    const spec = { type: 'bar_model', bars: [{ label: 'Ali', units: 2 }, { label: 'Ben', units: 3 }] } as DiagramSpec
    render(DiagramView, { spec, keyOnly: true })
    expect(screen.getByText(/printed in the answer key only, not on the student paper/)).toBeInTheDocument()
  })

  it('says nothing for question figures', () => {
    const spec = { type: 'shaded_fraction', shape: 'bar', parts: 4, shaded: [0] } as unknown as DiagramSpec
    render(DiagramView, { spec })
    expect(screen.queryByText(/answer key only/)).toBeNull()
  })

  it('says nothing for a bank question, whose bar model may be part of the question', () => {
    const spec = { type: 'bar_model', bars: [{ label: 'Ali', units: 2 }] } as DiagramSpec
    render(DiagramView, { spec, keyOnly: false })
    expect(screen.queryByText(/answer key only/)).toBeNull()
  })
})
