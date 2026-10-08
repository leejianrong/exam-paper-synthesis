# ADR-0022: Hosted multi-teacher SaaS — Fly.io + Neon Postgres, tenant-scoped from day one

- Status: Accepted
- Deciders: project owner
- Supersedes: ADR-0017 (local single-user SQLite bank)
- Related: ADR-0001 (single-user/no server state — now reversed), ADR-0021, `docs/planning/editor/WYSIWYG.md`

## Context

ADR-0017 chose a local, single-user SQLite bank. The owner now intends a hosted SaaS
with multi-teacher support within October 2026, free to use.

## Decision

- **Hosting:** Fly.io (API + web) and **Neon** Postgres. The engine stays
  UI/HTTP-agnostic and DB-agnostic; persistence lives behind an interface at the API
  boundary (the existing `bank.py` interface is kept, with a Postgres implementation).
- **Tenant-scoped from the first slice:** documents, bank rows and assets carry an
  `owner_id`; every query is owner-filtered. Retrofitting tenancy later is the expensive
  path, so even the stub-auth first slice enforces it.
- **Content visibility:** *sourced* and *free-form* content is private to its owner —
  sourced past papers are licensed "internal practice use only", so they must never enter
  a shared bank. Only engine-generated content is shareable.
- **Assets:** free-form images go to object storage with per-file and per-account limits.
- **Pricing/quotas:** free. Limit **exports per account** (PDF generation runs headless
  Chromium: concurrency cap, timeout, per-account rate limit).
- **Login: social sign-in only — Google, Microsoft and GitHub (OAuth2/OIDC), no
  passwords.** No bespoke credential storage. Accounts are keyed by provider + provider
  subject id; the same person signing in via two providers is linked by **verified** email
  only (GitHub emails may be private/unverified — an unverified email never auto-links;
  it creates a separate account). Sessions are server-side cookies (HttpOnly, SameSite=Lax).
  Choice of library/service (e.g. Authlib in FastAPI vs a hosted broker) is a W3 detail.

## Consequences

- Reverses ADR-0001 / PRD "no server state"; the client-side worksheet tray is replaced by
  server-stored documents.
- Local CLI keeps working against a local/SQLite bank for dogfooding and tests.
