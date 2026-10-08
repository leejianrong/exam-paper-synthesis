# Launch checklist (W4)

What the code does for you is listed first; what only **you** can do (accounts, secrets, DNS)
is the checklist below it. Target: October 2026, Fly.io + Neon (ADR-0022).

## Already in the repo

- **One production image** (`Dockerfile`): builds the web app, installs the API and headless
  Chromium, runs as a non-root user, serves the SPA and the API on one origin (first-party
  cookies, no CORS). `fly.toml` runs it on a 2 GB machine with `/ready` as the health check.
- **Refuses to boot unsafe** (`EXAM_ENV=production`, set in the image): dev identity stub on,
  no `EXAM_DATABASE_URL`, non-https public/web URL, or no sign-in provider ⇒ startup error that
  names each problem. API docs/OpenAPI are off in production.
- **Security headers** on every response (`nosniff`, `X-Frame-Options: SAMEORIGIN`, referrer and
  permissions policies, HSTS on https). Session cookie: HttpOnly, SameSite=Lax, Secure on https.
- **Export protection**: per-account allowance (30/day, 5/minute; `docs/AUTH.md`), a
  concurrency cap (`EXAM_EXPORT_CONCURRENCY`, default 2; 503 when busy), a per-operation
  browser timeout (`EXAM_EXPORT_TIMEOUT_MS`, default 30 s), refund on a failed render.
- **Isolation**: every document/asset/bank/session row is owner-scoped; a foreign id is a 404;
  tests run on both SQLite and Postgres.
- `/health` (liveness, no DB) and `/ready` (DB reachable; 503 without leaking internals).

## Before the first user (you)

1. **Neon**: create the project; copy the **pooled** connection string (`sslmode=require`).
   Turn on point-in-time restore (the free tier's window is short — note it; upgrade or add a
   nightly `pg_dump` if you want longer retention).
2. **OAuth apps** (`docs/AUTH.md`): Google, Microsoft, GitHub, each with callback
   `https://<host>/auth/<provider>/callback`.
3. **Fly**: `fly launch --no-deploy` (adjust `app`, region, URLs in `fly.toml`), then
   `fly secrets set EXAM_DATABASE_URL=… EXAM_OAUTH_GOOGLE_CLIENT_ID=… EXAM_OAUTH_GOOGLE_CLIENT_SECRET=…`
   (and Microsoft/GitHub), then `fly deploy`. The app will not start until the environment is
   right — read the error it prints.
4. **Smoke test on the real host**: sign in with each provider; create a paper; add a generated,
   a bank (import a file) and a free-form question with an image and an equation; export student,
   key and full PDFs; check the PDF fonts and the figure; sign out and confirm `/documents` is 401.
5. **Cloudflare edge (KAN-305)**: proxy the domain, TLS "Full (strict)", WAF/rate-limit rules on
   `/auth/*` and `/export` paths, cache static assets. Then set `EXAM_PUBLIC_URL`/`EXAM_WEB_URL`
   to the public domain and update the OAuth callback URLs.
6. **Backups drill**: restore a Neon branch to a point in time once, so the first time is not an
   emergency.
7. **Policy pages**: privacy notice (what is stored: email, name, papers, images; no passwords),
   terms (free, export limit, private content), and a contact address. Both privacy promises are
   built: `GET /account/export` (zip of JSON + images) and `DELETE /account` (see AUTH.md); the
   notice can link them from the account menu. Sourced past-paper content
   is "internal practice use only" — it stays private to its owner by design; do not add any
   shared bank of it.
8. **Monitoring**: an uptime check on `/ready`; Fly metrics/alerts for memory (Chromium) and 5xx;
   log review for `export is busy` (503) and 429 volume to tune the limits.
9. **Load sanity**: ~10 simultaneous exports should queue/503 cleanly, not crash the machine
   (raise the VM size or `EXAM_EXPORT_CONCURRENCY` deliberately, not by accident).

## Known follow-ups (not blockers)

- Object storage for images if Postgres size becomes a concern (the `AssetStore` protocol allows it).
