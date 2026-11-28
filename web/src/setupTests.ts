// Extends Vitest's `expect` with jest-dom matchers (toBeInTheDocument, …) and
// auto-cleans the DOM between tests. Loaded via vite.config.ts `test.setupFiles`.
import '@testing-library/jest-dom/vitest'

// ProseMirror measures layout through Range/Element geometry APIs jsdom does not
// implement; stub them so the TipTap editor can run under jsdom (W1c).
const emptyRect = { x: 0, y: 0, width: 0, height: 0, top: 0, left: 0, bottom: 0, right: 0, toJSON: () => ({}) }
if (typeof Range !== 'undefined') {
  Range.prototype.getBoundingClientRect = () => emptyRect as DOMRect
  Range.prototype.getClientRects = () =>
    ({ length: 0, item: () => null, [Symbol.iterator]: [][Symbol.iterator] }) as unknown as DOMRectList
}
if (typeof document !== 'undefined' && !document.elementFromPoint) {
  document.elementFromPoint = () => null
}

// jsdom has no ResizeObserver (Svelte's bind:clientHeight uses it); a no-op is enough.
if (typeof globalThis.ResizeObserver === 'undefined') {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
}

// Since jsdom 31 an iframe whose srcdoc is set after it joined the page fires no load event
// (a browser fires one for each srcdoc it shows), so the answer key view never sees its frame
// draw. Fire it as a browser would, after the current task.
if (typeof HTMLIFrameElement !== 'undefined') {
  const srcdoc = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'srcdoc')
  const setAttribute = HTMLIFrameElement.prototype.setAttribute
  const loadLater = (frame: HTMLIFrameElement) =>
    setTimeout(() => frame.isConnected && frame.dispatchEvent(new Event('load')))
  if (srcdoc?.set) {
    Object.defineProperty(HTMLIFrameElement.prototype, 'srcdoc', {
      ...srcdoc,
      set(this: HTMLIFrameElement, value: string) {
        srcdoc.set!.call(this, value)
        loadLater(this)
      },
    })
  }
  // jsdom's own load, for the blank document it puts in the frame, would be a second one:
  // swallow it so each srcdoc frame sees exactly one load, as in a browser
  document.addEventListener(
    'load',
    (e) => {
      if (e.isTrusted && e.target instanceof HTMLIFrameElement && e.target.hasAttribute('srcdoc'))
        e.stopImmediatePropagation()
    },
    true,
  )
  HTMLIFrameElement.prototype.setAttribute = function (name: string, value: string) {
    setAttribute.call(this, name, value)
    if (name.toLowerCase() === 'srcdoc') loadLater(this)
  }
}
