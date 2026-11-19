import { describe, it, expect, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte'
import ConfirmDialog from './ConfirmDialog.svelte'

function setup() {
  const onConfirm = vi.fn()
  const onCancel = vi.fn()
  render(ConfirmDialog, {
    props: { title: 'Regenerate?', body: 'Replaces 13 unlocked questions.', confirmLabel: 'Regenerate', onConfirm, onCancel },
  })
  return { onConfirm, onCancel }
}

describe('ConfirmDialog', () => {
  it('names the action, focuses the confirm button and confirms', async () => {
    const { onConfirm } = setup()
    const dialog = screen.getByRole('alertdialog', { name: 'Regenerate?' })
    expect(dialog).toHaveAccessibleDescription('Replaces 13 unlocked questions.')
    const go = screen.getByRole('button', { name: 'Regenerate' })
    expect(go).toHaveFocus()
    await fireEvent.click(go)
    expect(onConfirm).toHaveBeenCalledOnce()
  })

  it('Escape and Cancel back out; Tab stays inside', async () => {
    const { onCancel } = setup()
    const dialog = screen.getByRole('alertdialog')
    await fireEvent.keyDown(dialog, { key: 'Tab' })
    expect(screen.getByRole('button', { name: 'Cancel' })).toHaveFocus()
    await fireEvent.keyDown(dialog, { key: 'Tab' })
    expect(screen.getByRole('button', { name: 'Regenerate' })).toHaveFocus()
    await fireEvent.keyDown(dialog, { key: 'Escape' })
    await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(onCancel).toHaveBeenCalledTimes(2)
  })

  it('gives focus back to the control that opened it, once that control can take it again', async () => {
    const opener = document.createElement('button')
    opener.textContent = 'Regenerate 3 unlocked…'
    const panel = document.createElement('div')
    panel.append(opener)
    document.body.append(panel)
    opener.focus()
    const { unmount } = render(ConfirmDialog, {
      props: { title: 'Regenerate?', body: 'b', confirmLabel: 'Regenerate', onConfirm: () => {}, onCancel: () => {} },
    })
    expect(screen.getByRole('button', { name: 'Regenerate' })).toHaveFocus()
    // confirming starts the operation: the opener is disabled and the page inert while it runs
    opener.disabled = true
    panel.setAttribute('inert', '')
    unmount()
    expect(opener).not.toHaveFocus()
    panel.removeAttribute('inert')
    opener.disabled = false
    await waitFor(() => expect(opener).toHaveFocus())
    panel.remove()
  })

  it('a type-to-confirm dialog needs the word and does nothing while busy', async () => {
    const onConfirm = vi.fn()
    const onCancel = vi.fn()
    const { rerender } = render(ConfirmDialog, {
      props: { title: 'Delete?', body: 'b', confirmLabel: 'Delete', confirmWord: 'DELETE', danger: true, onConfirm, onCancel },
    })
    const go = screen.getByRole('button', { name: 'Delete' })
    expect(screen.getByLabelText(/to confirm/)).toHaveFocus()
    expect(go).toBeDisabled()
    await fireEvent.input(screen.getByLabelText(/to confirm/), { target: { value: 'DELETE' } })
    expect(go).toBeEnabled()
    await rerender({ busy: true })
    expect(go).toBeDisabled()
    await fireEvent.keyDown(screen.getByRole('alertdialog'), { key: 'Escape' })
    expect(onCancel).not.toHaveBeenCalled()
  })
})
