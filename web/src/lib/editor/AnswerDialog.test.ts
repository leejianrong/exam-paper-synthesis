import { describe, it, expect, vi, afterEach } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/svelte'
import AnswerDialog from './AnswerDialog.svelte'
import { freeformDocNode } from './fixtures'

afterEach(() => vi.unstubAllGlobals())

describe('Edit answer… (EXA-162)', () => {
  it('waits for an image still uploading before it closes, so the image is not lost (review of #242)', async () => {
    let land: () => void = () => {}
    vi.stubGlobal(
      'fetch',
      vi.fn(
        () =>
          new Promise((done) => {
            land = () =>
              done({ ok: true, status: 201, json: async () => ({ id: 'a'.repeat(32), mime: 'image/png', width: 2, height: 3, bytes: 9 }) })
          }),
      ),
    )
    const onClose = vi.fn()
    const onAnswer = vi.fn()
    render(AnswerDialog, {
      props: { number: 4, block: freeformDocNode({ body: 'Draw it.' }), onAnswer, onPartAnswer: vi.fn(), onError: vi.fn(), onClose },
    })
    const dialog = screen.getByRole('dialog', { name: 'Answer to question 4' })
    const input = await waitFor(() => within(dialog).getByLabelText('Choose answer image') as HTMLInputElement)
    await fireEvent.change(input, { target: { files: [new File(['png'], 'fig.png', { type: 'image/png' })] } })

    // Done while the image is on its way: the dialog stays and says why
    await fireEvent.click(within(dialog).getByRole('button', { name: 'Done' }))
    expect(onClose).not.toHaveBeenCalled()
    expect(within(dialog).getByRole('status')).toHaveTextContent('Image still uploading…')
    expect(within(dialog).getByRole('status')).toHaveTextContent('Press Done again to close without it')

    // once it lands it goes into the answer, then the dialog closes as asked
    land()
    await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1))
    expect(JSON.stringify(onAnswer.mock.calls.at(-1)?.[0])).toContain('"type":"image"')
  })

  it('a stalled upload never traps the page: a second Done, or Esc, closes without the image (re-review of #242)', async () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {}))) // never lands
    for (const second of ['done', 'escape'] as const) {
      const onClose = vi.fn()
      const view = render(AnswerDialog, {
        props: { number: 2, block: freeformDocNode(), onAnswer: vi.fn(), onPartAnswer: vi.fn(), onError: vi.fn(), onClose },
      })
      const dialog = screen.getByRole('dialog', { name: 'Answer to question 2' })
      const input = await waitFor(() => within(dialog).getByLabelText('Choose answer image') as HTMLInputElement)
      await fireEvent.change(input, { target: { files: [new File(['png'], 'fig.png', { type: 'image/png' })] } })
      await fireEvent.click(within(dialog).getByRole('button', { name: 'Done' }))
      expect(onClose).not.toHaveBeenCalled()
      if (second === 'done') await fireEvent.click(within(dialog).getByRole('button', { name: 'Done' }))
      else await fireEvent.keyDown(dialog, { key: 'Escape' })
      expect(onClose).toHaveBeenCalledTimes(1)
      view.unmount()
    }
  })

  it('closes at once when nothing is uploading', async () => {
    const onClose = vi.fn()
    render(AnswerDialog, {
      props: { number: 1, block: freeformDocNode({ answer: 'Seven' }), onAnswer: vi.fn(), onPartAnswer: vi.fn(), onError: vi.fn(), onClose },
    })
    await fireEvent.click(screen.getByRole('button', { name: 'Done' }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
