# ADR-0001: Access and deployment model

- Status: Accepted
- Deciders: project owner
- Related: Q-A1, Q-A2, Q-A3

## Context

The MVP must let a real user try the tool and generate output, but the earlier
plan flagged auth, multi-tenancy, and billing as out of scope. We need to fix how
the MVP is accessed and by whom.

## Decision

- The MVP is **self-serve**: a user drives the Svelte UI and generates output
  themselves (not a concierge/founder-operated pipeline).
- The MVP is **single-user**: no login, no accounts, no tenancy. It runs as a
  single deployment (local dev or one hosted instance) with no per-user data
  separation.
- **Multi-user with authentication and authorization is a deliberate future
  phase**, not part of the MVP.

## Consequences

- No auth/session/tenant code in the MVP; the API can assume a single implicit user.
- Persistence of a per-user "library" is deferred and depends on Q-A3 (still open:
  ephemeral vs saved).
- The architecture should avoid choices that make adding auth/multi-tenancy hard
  later (keep the API stateless where reasonable; scope data by a future user id).
