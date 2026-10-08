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
