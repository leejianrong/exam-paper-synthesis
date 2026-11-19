// Ask before an action from code that has no page of its own to render a dialog in (a
// question's node view lives inside the editor): mounts a ConfirmDialog on the body and
// resolves true on confirm, false on cancel.
import { mount, unmount } from 'svelte'
import ConfirmDialog from './ConfirmDialog.svelte'

export function confirmAction(opts: { title: string; body: string; confirmLabel: string }): Promise<boolean> {
  return new Promise((resolve) => {
    const target = document.createElement('div')
    document.body.append(target)
    const done = (ok: boolean) => {
      void unmount(dialog)
      target.remove()
      resolve(ok)
    }
    const dialog = mount(ConfirmDialog, {
      target,
      props: { ...opts, onConfirm: () => done(true), onCancel: () => done(false) },
    })
  })
}
