# Accounts and sign-in (W3a)

Social sign-in only (ADR-0022): **Google, Microsoft, GitHub**. No passwords are stored.

## Configure (environment)

| Variable | Meaning |
|---|---|
| `EXAM_OAUTH_{GOOGLE,MICROSOFT,GITHUB}_CLIENT_ID` / `_CLIENT_SECRET` | Both set ⇒ that provider is offered on the login page. |
| `EXAM_PUBLIC_URL` | The API's external base URL (default `http://localhost:8000`). Redirect URIs are built from it; `https://…` also turns on `Secure` cookies. |
| `EXAM_WEB_URL` | The web app's URL (default `http://localhost:5173`). The only place the API ever redirects to, and the default CORS origin. |
| `EXAM_CORS_ORIGINS` | Optional comma-separated override of the allowed web origins. |
| `EXAM_AUTH_PATH` | SQLite accounts DB (default `~/.exam_engine/accounts.sqlite3`; Postgres arrives in W3b). |
| `EXAM_DEV_AUTH=1` | Local development stub: no sign-in, owner = `X-Dev-Owner` (default `local`). A valid session still wins. **Never set in production** — without it, anonymous requests are 401. |

## Register with each provider

Redirect (callback) URI: `{EXAM_PUBLIC_URL}/auth/{google|microsoft|github}/callback`.

- **Google**: OAuth client (Web application); scopes `openid email profile`.
- **Microsoft**: Entra app registration, accounts in any org directory and personal accounts ("common"); a client secret.
- **GitHub**: OAuth App (not a GitHub App); scopes `read:user user:email`.

## Behaviour worth knowing

- Flow: `/auth/{provider}/login` → provider → `/auth/{provider}/callback` → session cookie → web app. `state` is bound to the browser by an HttpOnly cookie (login CSRF) and PKCE S256 is used. The profile is read from the provider's userinfo endpoint with the access token just obtained from its token endpoint.
- Session: random token, stored hashed, 30 days; cookie `exam_session` is HttpOnly, SameSite=Lax. `POST /auth/logout` deletes it. `GET /auth/me` says who you are.
- Linking: a second provider reaches the same account **only** when both sides have a *verified* email (Google's `email_verified`; GitHub's primary verified address). Microsoft does not assert verification, so its email never links. An unverified email never links or claims an address.
- Documents, bank rows and assets are owned by the user id; a foreign id is always 404.

## Your data: export and deletion (W5)

Both are in the account menu (click your name). `GET /account/export` returns a zip: `account.json`, `documents/<id>.json`, `bank/<n>-<id>.json`, and every image as its original bytes in `assets/` with an `assets/index.json`. `DELETE /account` with body `{"confirm": "DELETE"}` erases the documents, images, bank rows, export-allowance events, sessions, linked sign-ins and the user row, then clears the cookie; anything else is a 422 and changes nothing. Signing in again with the same Google/Microsoft/GitHub identity afterwards starts a new, empty account (and a fresh export allowance).

## Export allowance (W3c)

PDF export is the expensive step (headless Chromium), so each account has a rolling allowance:

| Variable | Default | Meaning |
|---|---|---|
| `EXAM_EXPORT_LIMIT_PER_DAY` | 30 | PDF exports in the last 24 hours (`0` = unlimited) |
| `EXAM_EXPORT_LIMIT_PER_MINUTE` | 5 | PDF exports in the last minute (`0` = unlimited) |
| `EXAM_USAGE_PATH` | `~/.exam_engine/usage.sqlite3` | the ledger |

Over the limit ⇒ **429** with `Retry-After` and a plain message. Previews, conversion and everything else are free; a render that fails is refunded. `GET /auth/quota` reports what is left (the editor shows "N exports left today"). All PDF routes — documents and the classic `/export/*` — now require a signed-in owner and share this allowance and the concurrency cap.

## Database (W3b)

`EXAM_DATABASE_URL` (a Postgres/Neon connection string, `sslmode=require`) switches **every** store — documents, assets, bank, accounts/sessions, export ledger — to Postgres; unset, they use the SQLite files above. Tables are created on first boot (idempotent, guarded by an advisory lock). Use Neon's pooled endpoint if you like: prepared statements are off, so pgbouncer transaction mode is fine. `EXAM_DB_POOL_MAX` (default 5) sizes the per-process pool.

Tests: `EXAM_TEST_DATABASE_URL` enables the Postgres contract tests (each in its own throwaway schema); add `EXAM_TEST_BACKEND=postgres` to run the whole API suite on Postgres. CI does both. Locally: `docker run -d -p 55432:5432 -e POSTGRES_PASSWORD=pw -e POSTGRES_DB=exam postgres:16-alpine`.

Data in the SQLite files does not migrate automatically; the dev-stub owner `local` has no counterpart in a production database (accounts get fresh ids). `mathgen` keeps using the local SQLite bank.

## Content-Security-Policy (W5)

Every API response carries a CSP (`api/app/csp.py`; `/docs` is exempt and only exists outside production). Scripts: `'self'` plus the SHA-256 of the three inline print scripts (KaTeX, auto-render, bootstrap) — no `'unsafe-inline'`, no `'unsafe-eval'`. Hashes rather than a nonce because the SPA is a static file and those scripts are identical for every document; the editor's preview iframe (`srcdoc`) and the classic page's `blob:` preview *inherit* the parent's policy, and the hashes let exactly those scripts run. Styles keep `'unsafe-inline'` (print HTML `<style>` blocks, `style` attributes); fonts and images are self/`data:`. If you change `render.py`'s inline scripts the hashes follow automatically (`inline_script_hashes()`); if you add a new inline script anywhere, `tests/test_csp.py` and `tests/e2e/csp.spec.js` fail. The e2e spec runs the built SPA and API on one origin (:8001), because the Vite dev server never sends the policy.
