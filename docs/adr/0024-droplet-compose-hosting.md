# ADR-0024: Host on one DigitalOcean droplet with Docker Compose

- Status: Accepted
- Deciders: project owner
- Supersedes: the hosting part of ADR-0022 (Fly.io + Neon). Tenancy, sign-in and content
  visibility in ADR-0022 are unchanged.
- Related: EXA-E16, `deploy/`, `docs/deploy/DROPLET.md`, `docs/deploy/BACKUPS.md`, `docs/LAUNCH.md`

## Context

ADR-0022 chose Fly.io for the app and Neon for Postgres. Before launch the owner preferred one
small server they control, at a fixed low price, in Singapore next to the teachers who use it.
The app is already one container (`Dockerfile`: the API serving the built web app, with headless
Chromium for PDFs), and every store has a tested Postgres implementation, so a single host needs
no code change.

## Decision

- **Host:** one DigitalOcean droplet in SGP1, Basic 1 GB / 1 vCPU (amended 2026-11-23, was
  2 GB: one PDF render peaks at ~370 MB, so a 1 GB box with one render at a time and 2 GB swap is
  enough while the owner is the only user; resize to 2 GB when use grows), Ubuntu 24.04,
  created with `doctl` by `deploy/provision.sh` and prepared on first boot by
  `deploy/cloud-init.yaml`, following `docs/deploy/DROPLET.md`.
- **Stack:** Docker Compose (`deploy/compose.yaml`): **Caddy** terminates TLS with automatic
  Let's Encrypt certificates and is the only service with published ports; the **app** image is
  pulled from GHCR (published by `.github/workflows/image.yml` on every merge to main, tagged
  `:latest` and `:sha-<commit>`); **Postgres 17** runs in a container on a named volume. Each
  service has a memory limit sized for the 1 GB box, raised from `.env` after a resize.
- **Database:** Postgres in the stack, not a managed database: cheapest, and the app's pool needs
  at most 5 connections. Nightly `pg_dump` to a DigitalOcean Spaces bucket, with a rehearsed
  restore (`docs/deploy/BACKUPS.md`). SQLite in production was considered and rejected: it
  would need an opt-in past the production gate now and a copy to Postgres later, while the
  Postgres code already exists.
- **Hostname:** `<droplet-ip>.sslip.io` until a domain is bought. The product will grow beyond
  PSLE maths (other subjects and syllabuses), so the domain should not name either.
- **Edge:** no Cloudflare for now; the droplet's cloud firewall allows only TCP 22, 80 and 443
  and UDP 443 (HTTP/3).
- **Sign-in at launch:** Google and GitHub. Microsoft stays supported in code, unconfigured.
- **Deploys** are manual
  (`git pull && docker compose pull --ignore-buildable && docker compose up -d --build`);
  rollback pins `APP_TAG` to an earlier sha.
- **Data:** production starts empty; nothing is carried over from local development stores.

## Consequences

- One box is a single point of failure: a droplet outage is an app outage until it is rebuilt
  from the runbook and the last dump (up to a day of data lost). Acceptable for a free product
  at this size; revisit with managed Postgres or a second droplet if users depend on it.
- The owner patches the host: Ubuntu security updates are automatic (with reboots at 03:30
  SGT); Docker and the image are updated by hand.
- `fly.toml` is removed. A later move to the owner's homelab Kubernetes cluster remains possible
  (the same image and environment), but is not planned here.
- Client addresses for the sign-in rate limits come from Caddy's `X-Forwarded-For` through
  uvicorn's proxy headers, which is exact for IPv4; the domain gets no AAAA record until IPv6 is
  enabled on the stack's network.
