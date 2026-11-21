# Launch checklist

What the code does for you is listed first; what only **you** can do (accounts, secrets, DNS)
is the checklist below it. Hosting: one DigitalOcean droplet running Docker Compose
([ADR-0024](adr/0024-droplet-compose-hosting.md)); the server set-up is in
[deploy/DROPLET.md](deploy/DROPLET.md), backups in [deploy/BACKUPS.md](deploy/BACKUPS.md).

## Already in the repo

- **One production image** (`Dockerfile`): builds the web app, installs the API and Chromium's
  headless shell, runs as a non-root user, serves the SPA and the API on one origin (first-party
  cookies, no CORS). The `Image` workflow builds it on every pull request, prints a paper with
  it, and on main pushes `ghcr.io/leejianrong/exam-paper-synthesis:latest` and `:sha-<commit>`.
- **The stack** (`deploy/compose.yaml`): Caddy (automatic TLS, the only published ports) → the
  app (`shm_size` 512 MB for Chromium, a memory limit, a health check) → Postgres 17 on a
  volume; a nightly backup to DigitalOcean Spaces. `deploy/.env.example` lists every value.
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

1. **Domain (optional at first)**: until one is bought, HOST is `<droplet-ip>.sslip.io`. Buying
   one before going public avoids changing the URL later and makes Google sign-in simpler.
2. **Droplet**: steps 1–6 of [DROPLET.md](deploy/DROPLET.md) (droplet, cloud firewall, deploy
   user, swap, automatic updates, Docker with log rotation).
3. **Spaces bucket and keys** for backups ([BACKUPS.md](deploy/BACKUPS.md)).
4. **Policy pages** (EXA-185): `/privacy` and `/terms` live, with the contact address you chose.
   Google's consent screen links to them. What they must say: what is stored (email, name,
   papers, images; no passwords), the export allowance, that content is private to its owner,
   and the account export (`GET /account/export`) and delete (`DELETE /account`) options.
   Sourced past-paper content is "internal practice use only": it stays private to its owner by
   design; do not add any shared bank of it.
5. **Sign-in apps**: Google and GitHub, step 7 of DROPLET.md, callbacks
   `https://HOST/auth/<provider>/callback`. Publish the Google app when ready for the public.
6. **First deploy** (the GHCR image is already public): step
   8 of DROPLET.md.
7. **Smoke test on the real host**: sign in with each provider; create a paper; add a generated,
   a bank (import a file) and a free-form question with an image and an equation; export
   student, key and full PDFs and a Word file; check the PDF fonts and the figure; sign out and
   confirm `/documents` is 401.
8. **Backup drill**: run one backup by hand and restore it into a scratch database, as
   BACKUPS.md describes, so the first restore is not an emergency.
9. **Monitoring**: the uptime check on `/ready` and the droplet's resource alerts (step 9 of
   DROPLET.md); stop the app once to see the alert arrive.
10. **Load sanity**: ~10 simultaneous exports should queue/503 cleanly, not crash the box
    (watch `docker stats`; raise `EXAM_EXPORT_CONCURRENCY` or the droplet size deliberately,
    not by accident).

## Known follow-ups (not blockers)

- Cloudflare in front (WAF/rate rules on `/auth/*` and exports; set `EXAM_CLIENT_IP_HEADER` to
  `CF-Connecting-IP` and allow only Cloudflare's addresses to 80/443).
- Object storage for images if Postgres size becomes a concern (the `AssetStore` protocol allows it).
- A homelab Kubernetes move (same image and environment) if the owner wants it later.
