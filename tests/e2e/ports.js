// The ports of the servers the e2e run talks to (playwright.config.js boots them). Set
// E2E_API_PORT / E2E_WEB_PORT / E2E_CSP_PORT to run beside dev servers on the usual ports.
const port = (name, fallback) => Number(process.env[name] || fallback)

export const API_PORT = port('E2E_API_PORT', 8000)
export const WEB_PORT = port('E2E_WEB_PORT', 5173)
export const CSP_PORT = port('E2E_CSP_PORT', 8001)
export const PORTS_OVERRIDDEN = ['E2E_API_PORT', 'E2E_WEB_PORT', 'E2E_CSP_PORT'].some((n) => process.env[n])

/** The API's origin, for specs that call it directly. */
export const API = `http://localhost:${API_PORT}`
/** The production-shaped server's origin (built SPA + API), for the CSP spec. */
export const CSP_ORIGIN = `http://localhost:${CSP_PORT}`
/** Moved ports also get their own throwaway stores (and CSP build), apart from a default run's. */
export const E2E_SUFFIX = PORTS_OVERRIDDEN ? `-${API_PORT}` : ''
