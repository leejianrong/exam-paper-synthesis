// What went wrong, in words a teacher can act on (EXA-165). Every failed API call becomes an
// `ApiError` whose message is plain language: the status and the server's own detail stay on
// the error (and in the console), never in the text on screen.

export class ApiError extends Error {
  /** The HTTP status, or 0 when the server could not be reached at all. */
  status: number
  /** The server's `detail` (a string, or a structured object such as a 409's). */
  detail: unknown
  /** Seconds from a 429's Retry-After header, when it sent one. */
  retryAfter: number | null
  constructor(status: number, detail: unknown, retryAfter: number | null = null) {
    super(plainMessage(status, detail, retryAfter))
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
    this.retryAfter = retryAfter
  }
}

/** Throw the `ApiError` for a failed response. Only a JSON `detail` is the server's own words:
 *  a body that isn't JSON (a proxy's error page) leaves the detail empty, so its status text
 *  ("Payload Too Large") never reaches the screen. */
export async function fail(res: Response): Promise<never> {
  let detail: unknown = null
  try {
    const body = (await res.json()) as { detail?: unknown }
    detail = body.detail ?? body
  } catch {
    // not JSON: the status alone says what happened
  }
  const after = Number(res.headers?.get?.('retry-after'))
  const err = new ApiError(res.status, detail, Number.isFinite(after) && after > 0 ? after : null)
  console.warn(`API ${res.status}`, detail ?? res.statusText)
  throw err
}

/** The browser couldn't reach the server (offline, DNS, CORS, the server down). */
export function offline(cause: unknown): ApiError {
  console.warn('API unreachable', cause)
  return new ApiError(0, String(cause))
}

/** "40 seconds", "3 minutes", "2 hours": how long until a retry is allowed. */
export function waitText(seconds: number): string {
  const unit = (n: number, w: string) => `${n} ${w}${n === 1 ? '' : 's'}`
  if (seconds < 60) return unit(Math.ceil(seconds), 'second')
  if (seconds < 3600) return unit(Math.ceil(seconds / 60), 'minute')
  return unit(Math.ceil(seconds / 3600), 'hour')
}

// The server's lowercase details that name a missing thing, in the app's words.
const MISSING: Record<string, string> = {
  'document not found': "This paper doesn't exist or was deleted.",
  'folder not found': "This folder doesn't exist or was deleted.",
  'question not found': 'That question is no longer in the paper. Reload to get the latest version.',
  'no such question in your bank': 'That question is no longer in your question bank.',
  'unknown paper template': "That paper template doesn't exist any more. Reload the page.",
}

/** FastAPI's own replies for a route it doesn't have: not words for a teacher. */
const FRAMEWORK = new Set(['Not Found', 'Method Not Allowed'])

/** A server detail written for people: a whole sentence, starting with a capital. */
function sentence(detail: unknown): string | null {
  const text =
    typeof detail === 'string'
      ? detail
      : detail && typeof detail === 'object' && typeof (detail as { message?: unknown }).message === 'string'
        ? (detail as { message: string }).message
        : null
  return text && /^[A-Z]/.test(text) && !FRAMEWORK.has(text) ? text : null
}

/** A short lowercase detail that still says what was wrong ("image is larger than 2 MB"). */
function reason(detail: unknown): string | null {
  if (typeof detail !== 'string' || !detail || detail.length > 120 || /^invalid\b/i.test(detail)) return null
  const s = detail.charAt(0).toUpperCase() + detail.slice(1)
  return /[.!?]$/.test(s) ? s : `${s}.`
}

/** The words for a status (0 = unreachable) and the server's detail. */
export function plainMessage(status: number, detail: unknown = null, retryAfter: number | null = null): string {
  if (status === 0) return "Can't reach the server. Check your internet connection."
  if (status === 401) return "You're signed out. Sign in again to carry on."
  if (status === 403) return "You don't have access to this."
  if (status >= 500) {
    return status === 503
      ? 'The server is busy. Try again in a moment.'
      : 'Something went wrong on our side. Try again in a moment.'
  }
  const own = sentence(detail)
  if (own) return own
  if (status === 404) {
    return (typeof detail === 'string' && MISSING[detail]) || "It doesn't exist any more or was deleted."
  }
  if (status === 409) return 'This paper changed in another tab or window. Reload to get the latest version.'
  if (status === 429) {
    return retryAfter ? `Too many requests. Try again in ${waitText(retryAfter)}.` : 'Too many requests. Try again in a minute.'
  }
  if (status === 413) return reason(detail) ?? 'That is too large to send.'
  if (status === 400 || status === 422) return reason(detail) ?? "The server couldn't accept this, so nothing was changed."
  return `The server refused the request (error ${status}).`
}

/** Worth offering "Try again": the same request may well work in a moment. */
export function canRetry(e: unknown): boolean {
  if (!(e instanceof ApiError)) return false
  if (e.status === 429) return e.retryAfter === null || e.retryAfter <= 60 // not "in 3 hours"
  return e.status === 0 || e.status === 408 || e.status >= 500
}

/** The request may have done its work although no reply came back (a lost connection, a
 *  gateway error): a create asked again could make a second copy. */
export function mayHaveHappened(e: unknown): boolean {
  return e instanceof ApiError && (e.status === 0 || e.status >= 500)
}

/** A failed create, which is never retried for the teacher: it may have been made anyway. */
export function createFailedText(e: unknown, action: string): string {
  const text = errorText(e, action)
  return mayHaveHappened(e) ? `${text} Check Your papers before trying again.` : text
}

/** The text to show for a failure: what didn't happen (`action`, e.g. "Couldn't save"), then why. */
export function errorText(e: unknown, action?: string): string {
  let why: string
  if (e instanceof Error && e.message) why = e.message
  else {
    console.warn(e)
    why = 'Something unexpected went wrong. Try again.'
  }
  return action ? `${action}. ${why}` : why
}
