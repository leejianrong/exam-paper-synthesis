// The question block's inline forms (Edit names…, Edit numbers…, EXA-89): focus moves to the
// first field as soon as it is drawn (the fields come after a fetch), and Escape closes.

const FIELD = 'input, select, textarea'

export function formKeys(node: HTMLElement, onClose: () => void) {
  let close = onClose
  const focusFirst = () => {
    const field = node.querySelector<HTMLElement>(FIELD)
    if (!field) return false
    field.focus()
    return true
  }
  const observer = new MutationObserver(() => {
    if (focusFirst()) observer.disconnect()
  })
  if (!focusFirst()) observer.observe(node, { childList: true, subtree: true })
  const onKey = (e: KeyboardEvent) => {
    if (e.key !== 'Escape') return
    e.preventDefault()
    e.stopPropagation()
    close()
  }
  node.addEventListener('keydown', onKey)
  return {
    update(next: () => void) {
      close = next
    },
    destroy() {
      observer.disconnect()
      node.removeEventListener('keydown', onKey)
    },
  }
}
