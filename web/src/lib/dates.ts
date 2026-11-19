// Dates as Singapore teachers write them (EXA-166): "19 Nov 2026, 9:05 am" (en-SG), and on the
// papers list a relative time for a recent edit ("5 min ago", "yesterday, 4:40 pm").

const FULL = new Intl.DateTimeFormat('en-SG', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
})
const TIME = new Intl.DateTimeFormat('en-SG', { hour: 'numeric', minute: '2-digit' })

// Some ICU versions put a narrow no-break space before "am"; print a plain one.
const plain = (s: string): string => s.replace(/[\u202f\u00a0]/g, ' ')

/** "19 Nov 2026, 9:05 am", in the viewer's time zone. */
export function fullDate(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '' : plain(FULL.format(d))
}

const dayStart = (d: Date): number => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()

/**
 * When a paper was edited, to follow the word "edited": "just now", "5 min ago", "today, 9:05 am",
 * "yesterday, 4:40 pm", else the full date. A time a little ahead of `now` (another clock) is
 * "just now".
 */
export function editedWhen(iso: string, now: Date = new Date()): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const mins = Math.floor((now.getTime() - d.getTime()) / 60_000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins} min ago`
  const days = Math.round((dayStart(now) - dayStart(d)) / 86_400_000)
  if (days === 0) return `today, ${plain(TIME.format(d))}`
  if (days === 1) return `yesterday, ${plain(TIME.format(d))}`
  return plain(FULL.format(d))
}
