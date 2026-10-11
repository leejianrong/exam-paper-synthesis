import { describe, it, expect, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/svelte'
import AnswerArea from './AnswerArea.svelte'
import { buildDocument, type DocJSON } from './doc'
import { PX_PER_MM, clampSpaceMm, defaultSpaceMm, unitParts } from './layout'

describe('layout helpers', () => {
  it('mirrors the engine default: 20 mm plus 15 mm a mark, bigger than the old box', () => {
    expect([1, 2, 3, 4].map(defaultSpaceMm)).toEqual([35, 50, 65, 80])
    expect(defaultSpaceMm(null)).toBe(defaultSpaceMm(2))
    expect(defaultSpaceMm(0)).toBe(defaultSpaceMm(1))
  })
  it('rounds a drag to 5 mm and keeps it on the page', () => {
    expect(clampSpaceMm(52.4)).toBe(50)
    expect(clampSpaceMm(-20)).toBe(0)
    expect(clampSpaceMm(999)).toBe(250)
  })
  it('puts $ before the blank and degrees, % and words after it', () => {
    expect(unitParts('$')).toEqual({ before: '$', after: '' })
    expect(unitParts('degrees')).toEqual({ before: '', after: '°' })
    expect(unitParts('cm^2')).toEqual({ before: '', after: 'cm²' })
    expect(unitParts('')).toEqual({ before: '', after: '' })
    expect(unitParts(null)).toEqual({ before: '', after: '' })
  })
})

describe('AnswerArea', () => {
  it('draws the working space at its real size', () => {
    render(AnswerArea, { props: { marks: 2 } })
    const box = screen.getByTestId('answer-area').querySelector('.space') as HTMLElement
    expect(box.style.height).toBe(`${50 * PX_PER_MM}px`)
    expect(screen.getByRole('slider', { name: 'Working space height' })).toHaveAttribute(
      'aria-valuenow',
      '50',
    )
  })

  it('shows Ans: with the unit and the marks, by placement', async () => {
    const { rerender } = render(AnswerArea, {
      props: { marks: 3, unit: 'cm^2', placement: 'answer', editable: false },
    })
    const line = () => screen.getByTestId('answer-area').querySelector('.line') as HTMLElement
    expect(line()).toHaveTextContent('Ans:')
    expect(line()).toHaveTextContent('cm²')
    expect(line()).toHaveTextContent('[3]')
    await rerender({ marks: 3, unit: 'cm^2', placement: 'question', editable: false })
    expect(line()).not.toHaveTextContent('[3]')
    await rerender({ marks: 3, unit: '$', placement: 'both', editable: false })
    expect(line()).toHaveTextContent('$')
    expect(line()).toHaveTextContent('[3]')
  })

  it('labels a part: Ans: (a)', () => {
    render(AnswerArea, { props: { marks: 1, label: 'a', editable: false } })
    expect(screen.getByTestId('answer-area').querySelector('.line')).toHaveTextContent(/Ans:\s*\(a\)/)
  })

  it('resizes by keyboard in 5 mm steps and by preset', async () => {
    const onSpace = vi.fn()
    render(AnswerArea, { props: { marks: 2, onSpace } })
    const grip = screen.getByRole('slider', { name: 'Working space height' })
    await fireEvent.keyDown(grip, { key: 'ArrowDown' })
    expect(onSpace).toHaveBeenLastCalledWith(55)
    await fireEvent.keyDown(grip, { key: 'ArrowUp' })
    expect(onSpace).toHaveBeenLastCalledWith(45)
    await fireEvent.change(screen.getByRole('combobox', { name: 'Working space' }), {
      target: { value: 'XL' },
    })
    expect(onSpace).toHaveBeenLastCalledWith(130)
    await fireEvent.change(screen.getByRole('combobox', { name: 'Working space' }), {
      target: { value: 'default' },
    })
    expect(onSpace).toHaveBeenLastCalledWith(null)
  })

  it('reports a unit change, including "no unit"', async () => {
    const onUnit = vi.fn()
    render(AnswerArea, { props: { marks: 1, unit: 'cm', onUnit } })
    const select = screen.getByRole('combobox', { name: 'Answer unit' })
    await fireEvent.change(select, { target: { value: 'degrees' } })
    expect(onUnit).toHaveBeenLastCalledWith('degrees')
    await fireEvent.change(select, { target: { value: '' } })
    expect(onUnit).toHaveBeenLastCalledWith('')
  })
})

describe('saving layout', () => {
  const block = (attrs: Record<string, unknown>) => ({
    type: 'freeformQuestion',
    attrs: { block_id: 'ff_aaaa', marks: 2, ...attrs },
    content: [{ type: 'paragraph' }],
  })
  const doc = (n: object): DocJSON => ({ type: 'doc', content: [n as never] })

  it('drops unset layout overrides and keeps set ones', () => {
    const out = buildDocument('T', doc(block({ space_mm: null, ans_unit: null })))
    expect(out.content.content[0].attrs).not.toHaveProperty('space_mm')
    expect(out.content.content[0].attrs).not.toHaveProperty('ans_unit')
    const set = buildDocument('T', doc(block({ space_mm: 90, ans_unit: '' })))
    expect(set.content.content[0].attrs).toMatchObject({ space_mm: 90, ans_unit: '' })
  })

  it('writes the paper settings only when there are some', () => {
    expect(buildDocument('T', doc(block({})))).not.toHaveProperty('settings')
    expect(buildDocument('T', doc(block({})), { marks_placement: 'both' }).settings).toEqual({
      marks_placement: 'both',
    })
  })
})
