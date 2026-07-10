# Marketing site

The public landing page for **Exam Paper Synthesis**, hosted on GitHub Pages.
It is a single, hand-authored, fully self-contained page — one `index.html` with
all CSS and JS inlined, system fonts, and inline SVG. **No external network
requests, no build step, no dependencies.** Open `site/index.html` directly in a
browser and it renders exactly as deployed.

## Files

- `index.html` — the entire page (styles, script, and illustrative SVGs inlined).
- `README.md` — this note.

## How it deploys

`.github/workflows/pages.yml` builds and deploys `site/` to GitHub Pages on every
push to `main` that touches `site/**` (or the workflow itself), and on manual
`workflow_dispatch`. It uses `actions/configure-pages`, `actions/upload-pages-artifact`
(with `path: site`) and `actions/deploy-pages`, with `pages: write` +
`id-token: write` permissions and the `github-pages` environment.

## One-time setup (repo owner)

Pages must be told to use the Actions workflow as its source, once:

**Settings → Pages → Build and deployment → Source: "GitHub Actions".**

Or via the CLI:

```bash
gh api -X POST repos/leejianrong/exam-paper-synthesis/pages \
  -f build_type=workflow
```

After that, the site publishes automatically at
`https://leejianrong.github.io/exam-paper-synthesis/`.

## Editing

Edit `index.html` directly. Keep everything inline/local — do not add CDN links,
remote fonts, or external images, so the page stays offline-capable and
CSP-friendly.
