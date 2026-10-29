"""P6 spike: can we know which printed page each question lands on, and draw a per-page tally box?

Run (pypdf is a spike-only dependency, not a project one):

    uv run --with pypdf python scripts/spikes/p6_pagination.py [--papers N] [--keep DIR]

For N random papers it measures, against the *real* Chromium PDF as ground truth:

  A. naive    page = floor(top / page_height) on the continuous (unfragmented) layout
  B. simulate greedy fragmentation over the continuous layout (questions atomic, headings keep
              with next), i.e. what a second pass could compute from DOM measurements
  C. explicit wrap each simulated page into its own fixed-height ``.pg`` box carrying a tally
              box, print again, and check the PDF has exactly the predicted pages with every
              question (and its tally) on the page we said

Ground truth is read back from the PDF text (one unique marker per question).
"""

from __future__ import annotations

import argparse
import io
import random
import sys
from collections import Counter
from pathlib import Path

from exam_engine import generate
from exam_engine.document import DOCUMENT_SCHEMA_VERSION
from exam_engine.render import render_document_html
from playwright.sync_api import sync_playwright
from pypdf import PdfReader

# A4 at 96 dpi, with the print.css @page margin (18mm 16mm).
MM = 96 / 25.4
PAGE_W = (210 - 2 * 16) * MM
PAGE_H = (297 - 2 * 18) * MM


def para(text: str) -> dict:
    return {"type": "paragraph", "content": [{"type": "text", "text": text}]}


def freeform(marker: str, marks: int, space: int | None, body_lines: int) -> dict:
    body = " ".join(
        ["Ann bought some sweets and shared them equally among her friends."] * body_lines
    )
    attrs = {"block_id": f"b_{marker.lower()}", "marks": marks}
    if space is not None:
        attrs["space_mm"] = space
    return {"type": "freeformQuestion", "attrs": attrs, "content": [para(f"{marker} {body}")]}


def multipart(marker: str, part_marks: list[int]) -> dict:
    parts = [
        {
            "type": "freeformPart",
            "attrs": {"marks": m},
            "content": [para(f"{marker}{chr(97 + i)} work out part {chr(97 + i)}.")],
        }
        for i, m in enumerate(part_marks)
    ]
    return {
        "type": "freeformQuestion",
        "attrs": {"block_id": f"b_{marker.lower()}"},
        "content": [para(f"{marker} A tank is 40 cm by 25 cm by 30 cm."), *parts],
    }


def templated(marker: str, seed: int) -> dict:
    q = generate("ratio_medium", seed)
    return {
        "type": "templatedQuestion",
        "attrs": {"block_id": f"b_{marker.lower()}", "question": q},
    }


def make_paper(rng: random.Random, oversize: bool = False) -> tuple[dict, dict[str, int]]:
    """A random paper: sections, free-form, multi-part and generated questions."""
    blocks: list[dict] = []
    marks: dict[str, int] = {}
    n = rng.randint(8, 16)
    for i in range(1, n + 1):
        marker = f"QM{i:02d}"
        if i in (1, n // 2):
            blocks.append(
                {
                    "type": "section",
                    "attrs": {"title": f"Section {'A' if i == 1 else 'B'}", "mode": "short"},
                }
            )
        kind = rng.choice(["free", "free", "multi", "templated"])
        if kind == "free":
            m = rng.randint(1, 5)
            blocks.append(freeform(marker, m, rng.choice([None, 20, 45, 90]), rng.randint(1, 5)))
            marks[marker] = m
        elif kind == "multi":
            pm = [rng.randint(1, 3) for _ in range(rng.randint(2, 3))]
            blocks.append(multipart(marker, pm))
            marks[marker] = sum(pm)
        else:
            node = templated(marker, rng.randint(1, 500))
            blocks.append(node)
            marks[marker] = node["attrs"]["question"]["question"]["total_marks"]
            # templated text has no marker: tag it with a hidden paragraph-free comment below
    if oversize:
        # 250 mm of working space plus a long stem: taller than a 261 mm page.
        blocks.insert(len(blocks) // 2, freeform("QM99", 5, 250, 12))
        marks["QM99"] = 5
    doc = {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "title": "Spike paper",
        "content": {"type": "doc", "content": blocks},
    }
    return doc, marks


# --- browser side -----------------------------------------------------------------------------

# Collect the top-level items of the document body with their continuous-layout geometry.
MEASURE_JS = """
() => {
  const body = document.querySelector('.doc-body');
  const out = [];
  const origin = document.querySelector('.sheet').getBoundingClientRect().top + scrollY;
  for (const el of body.children) {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    out.push({
      cls: el.className,
      top: r.top + scrollY,
      bottom: r.bottom + scrollY,
      mb: parseFloat(cs.marginBottom) || 0,
      keepNext: cs.breakAfter === 'avoid' || cs.breakAfter === 'avoid-page',
      forced: cs.breakAfter === 'page',
      text: el.innerText,
      origin,
    });
  }
  return out;
}
"""

# Wrap each page's items in a fixed-height box with a tally box, in place.
WRAP_JS = """
([pages, h, head]) => {
  const body = document.querySelector('.doc-body');
  const kids = Array.from(body.children);
  const style = document.createElement('style');
  style.textContent = `
    .pg { position: relative; height: ${h}px; break-after: page; overflow: hidden; }
    .pg > :first-child { margin-top: 0 !important; }
    .tally { position: absolute; right: 0; bottom: 0; width: 22mm; height: 22mm;
             border: 1.5px solid #000; background:
             linear-gradient(to top right, transparent calc(50% - 1px), #000 calc(50% - 1px),
             #000 calc(50% + 1px), transparent calc(50% + 1px)); font: 600 12px Inter, sans-serif; }
    .tally span { position: absolute; right: 3mm; bottom: 2mm; }
  `;
  document.head.append(style);
  pages.forEach((p) => {
    const pg = document.createElement('div');
    pg.className = 'pg';
    if (p.first) pg.style.height = (h - head) + 'px';
    body.append(pg);
    p.items.forEach((i) => pg.append(kids[i]));
    const t = document.createElement('div');
    t.className = 'tally';
    t.innerHTML = `<span>TALLY${p.marks}</span>`;
    pg.append(t);
  });
}
"""


def simulate(items: list[dict]) -> list[int]:
    """Greedy fragmentation of the continuous layout: page index per item.

    Questions are atomic (``break-inside: avoid``); an item with ``break-after: avoid`` stays with
    the next one; a forced ``break-after: page`` ends the page. A taller-than-page item overflows
    onto the next page, as Chromium does (not modelled beyond keeping it on its start page).
    """
    page_of = [0] * len(items)
    page = 0
    base = items[0]["origin"] if items else 0.0
    i = 0
    while i < len(items):
        # a group is an item plus the run of keep-with-next items that lead into it
        j = i
        while j < len(items) - 1 and items[j]["keepNext"]:
            j += 1
        group_top, group_bottom = items[i]["top"], items[j]["bottom"]
        if group_bottom - base > PAGE_H and group_top > base + 0.5:
            page += 1
            base = group_top
        for k in range(i, j + 1):
            page_of[k] = page
        if items[j]["forced"]:
            page += 1
            base = items[j + 1]["top"] if j + 1 < len(items) else base
        i = j + 1
    return page_of


def naive(items: list[dict]) -> list[int]:
    origin = items[0]["origin"] if items else 0.0
    return [int((it["top"] - origin) // PAGE_H) for it in items]


def words(pages: list[str]) -> Counter:
    return Counter(w for t in pages for w in t.split() if not w.startswith("TALLY"))


def marker_of(text: str) -> str | None:
    import re

    m = re.search(r"QM\d\d", text)
    return m.group(0) if m else None


def pdf_pages(pdf: bytes) -> list[str]:
    return [p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages]


def truth(pages: list[str], markers: list[str]) -> dict[str, int]:
    return {m: next((i for i, t in enumerate(pages) if m in t), -1) for m in markers}


def run(papers: int, keep: Path | None, oversize: bool = False) -> int:
    rng = random.Random(20261029)
    tot = {
        "items": 0,
        "naive": 0,
        "sim": 0,
        "wrap_pages": 0,
        "wrap_ok": 0,
        "wrap_tally": 0,
        "papers": 0,
        "lost": 0,
        "tall": 0,
    }
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": round(PAGE_W), "height": 1000})
            page.emulate_media(media="print")
            for n in range(papers):
                doc, marks = make_paper(rng, oversize)
                html = render_document_html("Spike", doc, mode="student")
                page.set_content(html, wait_until="load")
                page.wait_for_selector("html[data-katex-rendered='true']", state="attached")
                items = page.evaluate(MEASURE_JS)
                pdf = page.pdf(format="A4", print_background=True)
                gt_pages = pdf_pages(pdf)
                # items that carry a marker (free-form and multi-part); templated ones are checked
                # through the page count and their neighbours.
                tagged = [(i, marker_of(it["text"])) for i, it in enumerate(items)]
                tagged = [(i, m) for i, m in tagged if m]
                gt = truth(gt_pages, [m for _, m in tagged])
                sim, nai = simulate(items), naive(items)
                a = sum(nai[i] == gt[m] for i, m in tagged)
                b = sum(sim[i] == gt[m] for i, m in tagged)

                # C: explicit pages, tallies, print again.
                n_pages = max(sim) + 1 if sim else 0
                groups = [{"items": [], "marks": 0, "first": k == 0} for k in range(n_pages)]
                for i, pg in enumerate(sim):
                    groups[pg]["items"].append(i)
                    m = marker_of(items[i]["text"])
                    if m:
                        groups[pg]["marks"] += marks[m]
                head = items[0]["top"] - items[0]["origin"]
                page.evaluate(WRAP_JS, [groups, PAGE_H - 2, head])
                pdf2 = page.pdf(format="A4", print_background=True)
                pages2 = pdf_pages(pdf2)
                gt2 = truth(pages2, [m for _, m in tagged])
                c_ok = sum(gt2[m] == sim[i] for i, m in tagged)
                # Nothing may be lost: the wrapped print has the same words as the plain one
                # (a taller-than-page item inside an overflow:hidden box would silently clip).
                lost = sum((words(gt_pages) - words(pages2)).values())
                tall = sum(it["bottom"] - it["top"] > PAGE_H for it in items)
                tot["lost"] += lost
                tot["tall"] += tall
                tally_ok = sum(
                    f"TALLY{g['marks']}" in pages2[k]
                    for k, g in enumerate(groups)
                    if k < len(pages2)
                )

                print(
                    f"paper {n + 1:2d}: {len(items):2d} items, {len(gt_pages)} pages | "
                    f"naive {a}/{len(tagged)}  simulate {b}/{len(tagged)} | "
                    f"wrapped: {len(pages2)} pages (predicted {n_pages}), "
                    f"questions on predicted page {c_ok}/{len(tagged)}, "
                    f"tallies {tally_ok}/{n_pages}, "
                    f"words lost {lost}, taller-than-page items {tall}"
                )
                tot["items"] += len(tagged)
                tot["naive"] += a
                tot["sim"] += b
                tot["papers"] += 1
                tot["wrap_pages"] += len(pages2) == n_pages
                tot["wrap_ok"] += c_ok
                tot["wrap_tally"] += tally_ok == n_pages
                if keep:
                    keep.mkdir(parents=True, exist_ok=True)
                    (keep / f"paper{n + 1:02d}_plain.pdf").write_bytes(pdf)
                    (keep / f"paper{n + 1:02d}_wrapped.pdf").write_bytes(pdf2)
        finally:
            browser.close()
    t = tot["items"]
    print(
        f"\nOVERALL over {tot['papers']} papers, {t} tagged questions\n"
        f"  A naive    : {tot['naive']}/{t} ({100 * tot['naive'] / t:.0f}%)\n"
        f"  B simulate : {tot['sim']}/{t} ({100 * tot['sim'] / t:.0f}%)\n"
        f"  C wrapped  : page count matches in {tot['wrap_pages']}/{tot['papers']} papers; "
        f"questions on predicted page {tot['wrap_ok']}/{t}; "
        f"all tallies on their page in {tot['wrap_tally']}/{tot['papers']} papers; "
        f"words lost {tot['lost']}; taller-than-page items {tot['tall']}"
    )
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--papers", type=int, default=12)
    ap.add_argument("--oversize", action="store_true", help="add a taller-than-page question")
    ap.add_argument("--keep", type=Path, default=None, help="write the PDFs here")
    args = ap.parse_args()
    sys.exit(run(args.papers, args.keep, args.oversize))
