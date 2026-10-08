// The one way the SPA calls the API: always with the session cookie, and a 401 anywhere means
// the session is gone (so the app shows the login page instead of a pile of failed requests).

import { sessionLost } from './session'

export async function apiFetch(url: string, init: RequestInit = {}): Promise<Response> {
  const res = await fetch(url, { ...init, credentials: 'include' })
  if (res.status === 401) sessionLost()
  return res
}
