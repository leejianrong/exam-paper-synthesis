# ADR-0008: Export / PDF engine

- Status: Proposed
- Deciders: project owner
- Related: Q-I1, Q-I2, Q-I3, Q-I5

## Context

The MVP must produce a printable worksheet and answer key. The Svelte UI already
renders an HTML preview with math and inline SVG diagrams. We want print output
that matches the preview without maintaining a second rendering path.

## Decision (proposed)

- Generate PDFs via **HTML → PDF using headless Chromium (Playwright)**.
- The same HTML/CSS pipeline feeds both the on-screen preview and the PDF
  (WYSIWYG), rendering inline SVG diagrams and KaTeX math natively; worksheet
  layout uses print CSS (`@page`, page-break rules).
- **Typst** is the designated fast-follow if precise multi-column exam layout is
  later required; **WeasyPrint** is the lighter fallback if Chromium's footprint
  becomes a problem (requires server-side math pre-render).

## Consequences

- Preview and print cannot diverge (single source of truth for layout).
- Chromium is a heavy runtime dependency; long-math pagination may need tuning.

## Open

- Worksheet layout minimums — columns, answer spaces, header, numbering (Q-I2).
- One combined document vs separate worksheet/answer-key exports (Q-I3).
- Math renderer choice in preview and how much LaTeX-style math primary needs (Q-I5).
