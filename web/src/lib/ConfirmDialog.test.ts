import { describe, it, expect, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/svelte'
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
})
