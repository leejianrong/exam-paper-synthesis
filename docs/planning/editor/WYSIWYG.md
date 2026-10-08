# WYSIWYG reframe — the editor is a document (initiative: `editor`)

> Supersedes the form-based editor direction (slices **E4**, **E5**). Decisions are
> recorded in ADR-0021 (document model + edit tiers) and ADR-0022 (SaaS hosting/tenancy).

## The idea

Teachers set papers in Word. The editor is a blank page; a big **+** area opens a choice:

- **Templated question** — from our bank / engine (blueprint generation on demand).
- **Free-form** — type text, paste equations, bring in their own PNG diagrams.

Templated questions carry an auto-generated answer key in a separate section at the end of
the document; free-form questions get an empty slot there for the teacher to fill in.

## Decisions (owner, 2026-10-07/08)

1. **Output: PDF only** while dogfooding (worksheet + answer key). `.docx` deferred.
2. **First user is the owner; multi-teacher SaaS within October 2026.** Free product.
3. **Hosting: Fly.io + Neon.** Export count limited per account.
4. **Templated edits are tiered** (ADR-0021): cosmetic slots free → numeric params via
   re-solve (later) → wording locked, with **Convert to free-form** as the escape hatch.
5. **Login: Google, Microsoft and GitHub sign-in** (OAuth/OIDC, no passwords; ADR-0022).

## What this changes

| Existing | Becomes |
|---|---|
| E1–E3 bank + schema v2 | Kept: substrate for the templated-question picker |
| E4 paper/section/group container | Absorbed into the document model (sections = headings, groups = grouped blocks) |
| E5 web form editor | Replaced by the WYSIWYG editor |
| ADR-0017 local SQLite bank | Superseded by ADR-0022 (Neon Postgres, tenant-scoped) |
| Client-side tray | Replaced by server-stored documents |

## Slices

| Slice | Title | Ends in (demo) |
|---|---|---|
| **W1** | Document model + editor shell — sub-slices **W1a** (done), **W1b** store/API, **W1c** editor UI, **W1d** bank tab; see [`W1-plan.md`](W1-plan.md) | Blank page → **+** inserts a templated block (picked from bank or generated, cosmetic-slot edits, in-block regenerate/harder/easier) → export worksheet + answer key (key at end) as PDF. Tenant-scoped storage (`owner_id`) with stub auth. TipTap/ProseMirror with custom node views. |
| **W2** | Free-form blocks — sub-slices **W2a** free-form block, **W2b** images + equations, **W2c** convert + bank import; see [`W2-plan.md`](W2-plan.md) | Free-form question with rich text, KaTeX equation node, PNG upload (object storage, size limits), marks field, empty answer slot; **Convert to free-form**; total marks across both block kinds. |
| **W3** | Accounts + Neon | Real login (method TBD), Postgres implementation of the bank/document store, per-account export quota and rate limit. |
| **W4** | Hardening + launch | Export concurrency cap/timeouts, backups, Cloudflare edge setup (KAN-305), launch checklist. |

Deferred: tier-2 numeric-parameter editing, nested/grouped shared-stem blocks (until a
real paper needs them), promote-free-form-to-bank, `.docx` export, live browser pagination
(W1 shows an A4-width page with page-break markers; true pagination comes from Chromium).

Risk: auth + tenancy is where the October date slips. If time runs short, cut tier-2
editing and grouped blocks first, never tenancy.

## Open questions

- ~~Param metadata~~ — resolved in [`W1a-param-roles-plan.md`](W1a-param-roles-plan.md)
  (`param_roles` block in blueprint YAML; `set-cosmetic` edit op).
