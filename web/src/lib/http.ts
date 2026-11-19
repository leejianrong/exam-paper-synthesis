// The one way the SPA calls the API: always with the session cookie, and a 401 anywhere means
// the session is gone (so the app shows the login page instead of a pile of failed requests).
// A request that never reaches the server rejects with an `ApiError` (status 0), so every
// caller words "offline" the same way (errors.ts).

import { offline } from './errors'
import { sessionLost } from './session'

/** `fetch` with the cookie; an unreachable server is an `ApiError(0)`. */
export async function reach(url: string, init: RequestInit = {}): Promise<Response> {
  try {
    return await fetch(url, { ...init, credentials: 'include' })
  } catch (e) {
    throw offline(e)
  }
}

export async function apiFetch(url: string, init: RequestInit = {}): Promise<Response> {
  const res = await reach(url, init)
  if (res.status === 401) sessionLost()
  return res
}
