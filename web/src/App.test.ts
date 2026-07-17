import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/svelte'

// Mock the API layer so Generate never hits the network; we only assert that
// the selector builds the right blueprint_code and passes it to generate().
const generate = vi.fn()
const editQuestion = vi.fn()
vi.mock('./lib/api', () => ({
  generate: (...args: unknown[]) => generate(...args),
  editQuestion: (...args: unknown[]) => editQuestion(...args),
}))

import App from './App.svelte'

beforeEach(() => {
  generate.mockReset()
  generate.mockResolvedValue([])
})

describe('App topic × difficulty selector', () => {
  it('defaults to Ratio / Medium → generate("ratio_medium", 1)', async () => {
    render(App)

    // Defaults are reflected in the two dropdowns.
    expect((screen.getByLabelText('Topic') as HTMLSelectElement).value).toBe('ratio')
    expect((screen.getByLabelText('Difficulty') as HTMLSelectElement).value).toBe('medium')

    await fireEvent.click(screen.getByRole('button', { name: 'Generate' }))

    expect(generate).toHaveBeenCalledTimes(1)
    expect(generate).toHaveBeenCalledWith('ratio_medium', 1)
  })

  it('builds the blueprint_code from the chosen topic + difficulty', async () => {
    render(App)

    await fireEvent.change(screen.getByLabelText('Topic'), {
      target: { value: 'geometry_area' },
    })
    await fireEvent.change(screen.getByLabelText('Difficulty'), {
      target: { value: 'hard' },
    })

    await fireEvent.click(screen.getByRole('button', { name: 'Generate' }))

    expect(generate).toHaveBeenCalledWith('geometry_area_hard', 1)
  })

  it('offers all six topics and three difficulties', () => {
    render(App)

    const topic = screen.getByLabelText('Topic') as HTMLSelectElement
    expect(topic.options).toHaveLength(6)
    expect([...topic.options].map((o) => o.value)).toEqual([
      'ratio',
      'fractions',
      'percentage',
      'speed',
      'geometry_angle',
      'geometry_area',
    ])

    const difficulty = screen.getByLabelText('Difficulty') as HTMLSelectElement
    expect([...difficulty.options].map((o) => o.value)).toEqual(['easy', 'medium', 'hard'])
  })
})
