import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/svelte'
import ChoiceOptions from './ChoiceOptions.svelte'
import type { ChoiceOption } from './types'

describe('ChoiceOptions layout (EXA-141)', () => {
  it('lists text options in one column, numbered (1) to (4), as the paper prints them', () => {
    const options: ChoiceOption[] = ['$12', '$18', '$24', '$36'].map((text, i) => ({
      label: String(i + 1),
      text,
    }))
    render(ChoiceOptions, { options })
    const list = screen.getByRole('list', { name: 'options' })
    expect(list).not.toHaveClass('grid')
    expect(screen.getByText('(1)')).toBeInTheDocument()
    expect(screen.getByText('(4)')).toBeInTheDocument()
  })

  it('keeps picture options in a grid', () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: true, json: async () => ({ svg: '<svg></svg>' }) })),
    )
    const options = [1, 2, 3, 4].map((i) => ({
      label: String(i),
      diagram: { type: 'cube_stack', view: 'front', heights: [[1]] },
    })) as unknown as ChoiceOption[]
    render(ChoiceOptions, { options })
    expect(screen.getByRole('list', { name: 'options' })).toHaveClass('grid')
    vi.unstubAllGlobals()
  })
})
