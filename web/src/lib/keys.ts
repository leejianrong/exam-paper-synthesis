// How a keyboard shortcut is shown and named (EXA-163). Shortcuts are written the PC way
// ("Ctrl+Alt+K"); on a Mac, Cmd plays Ctrl's part and labels use the Mac glyphs (⌥⌘K).

/** Is this a Mac (or iPad with a keyboard)? Cmd then plays Ctrl's part. */
export function isMac(): boolean {
  const nav = globalThis.navigator as (Navigator & { userAgentData?: { platform?: string } }) | undefined
  const platform = nav?.userAgentData?.platform || nav?.platform || ''
  return /mac|iphone|ipad/i.test(platform)
}

/** Does this key press type its character (`e.key`) rather than run a chord? Plain keys and
 *  Shift do; so does AltGr, which Windows reports as Ctrl+Alt (German AltGr+8 is "["), and ⌥ on
 *  a Mac (German Mac ⌥5 is "["). Ctrl or Cmd without AltGr, and Alt elsewhere, are chords. */
export function typesCharacter(e: KeyboardEvent, mac = isMac()): boolean {
  const altGraph = !!e.getModifierState?.('AltGraph')
  if (e.metaKey || (e.ctrlKey && !altGraph)) return false
  return !e.altKey || mac || altGraph
}

/** "Ctrl+Alt+K" as this computer's keyboard shows it: "⌥⌘K" on a Mac, unchanged elsewhere. */
export function keyLabel(shortcut: string, mac = isMac()): string {
  if (!mac) return shortcut
  const parts = shortcut.split('+')
  // a lone "+" key would split into empty strings; none of ours is one
  const key = parts.pop() ?? ''
  const mods = new Set(parts)
  const glyph: Record<string, string> = { Enter: '↩', Del: '⌫' }
  return (mods.has('Alt') ? '⌥' : '') + (mods.has('Shift') ? '⇧' : '') + (mods.has('Ctrl') ? '⌘' : '') + (glyph[key] ?? key)
}

/** The same shortcut as `aria-keyshortcuts` names keys ("Control+Alt+K", "Meta+K"). */
export function ariaKeys(shortcut: string, mac = isMac()): string {
  const names: Record<string, string> = {
    '↑': 'ArrowUp',
    '↓': 'ArrowDown',
    '↵': 'Enter',
    Del: 'Delete',
    Ctrl: mac ? 'Meta' : 'Control',
  }
  return shortcut
    .split('+')
    .map((k) => names[k] ?? k)
    .join('+')
}
