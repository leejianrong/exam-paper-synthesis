"""Place figure text clear of the strokes and of each other (EXA-136).

A renderer records every stroke it draws as an obstacle (segments; curves are
sampled into short segments), then asks :meth:`Layout.place` for each label with
a list of candidate centres in order of preference. The first candidate whose
estimated text box keeps ``CLEAR`` px from every stroke and every label already
placed wins. Text boxes are estimated from the font size and a generous per-glyph
width (Inter), so the estimate errs on the side of more space.

Pure and deterministic: candidates are tried in the order given.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Iterator

CLEAR = 3.0  # px of air between a label and a stroke or another label

_WIDE = set("mwMW%@")
_NARROW = set(" .,:;'il1|()°-ℓtfrjI")
_DESCENDERS = set("gjpqy(),")


def text_size(text: str, font_size: float) -> tuple[float, float, float]:
    """``(width, ascent, descent)`` of a single-line label, in px (estimate)."""
    em = sum(0.9 if c in _WIDE else 0.38 if c in _NARROW else 0.66 for c in text)
    descent = 0.25 if any(c in _DESCENDERS for c in text) else 0.06
    return em * font_size, 0.78 * font_size, descent * font_size


Box = tuple[float, float, float, float]  # x0, y0, x1, y1
Point = tuple[float, float]


def _seg_near_box(a: tuple[float, float], b: tuple[float, float], box: Box, pad: float) -> bool:
    """Does segment ab come within ``pad`` of the box (a capsule-vs-box test)?"""
    if not _seg_hits_box(a, b, (box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad)):
        return False
    return seg_box_distance(a, b, box) < pad


def seg_box_distance(a: tuple[float, float], b: tuple[float, float], box: Box) -> float:
    """Shortest distance from segment ab to the box (0 when they meet)."""
    if _seg_hits_box(a, b, box):
        return 0.0
    dx, dy = b[0] - a[0], b[1] - a[1]
    ll = dx * dx + dy * dy

    def to_seg(px: float, py: float) -> float:
        t = 0.0 if ll == 0 else max(0.0, min(1.0, ((px - a[0]) * dx + (py - a[1]) * dy) / ll))
        return math.hypot(a[0] + t * dx - px, a[1] + t * dy - py)

    def to_box(px: float, py: float) -> float:
        return math.hypot(max(box[0] - px, 0.0, px - box[2]), max(box[1] - py, 0.0, py - box[3]))

    corners = ((box[0], box[1]), (box[2], box[1]), (box[0], box[3]), (box[2], box[3]))
    return min([to_seg(*c) for c in corners] + [to_box(*a), to_box(*b)])


def _seg_hits_box(a: tuple[float, float], b: tuple[float, float], box: Box) -> bool:
    """Liang-Barsky: does segment ab meet the (closed) box?"""
    dx, dy = b[0] - a[0], b[1] - a[1]
    t0, t1 = 0.0, 1.0
    for p, q in (
        (-dx, a[0] - box[0]),
        (dx, box[2] - a[0]),
        (-dy, a[1] - box[1]),
        (dy, box[3] - a[1]),
    ):
        if p == 0:
            if q < 0:
                return False
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return False
    return True


def svg_arc_points(
    p0: tuple[float, float], r: float, large: int, sweep: int, p1: tuple[float, float]
) -> list[tuple[float, float]]:
    """The circular arc ``M p0 A r r 0 large sweep p1`` as a browser draws it, sampled
    every ~5 degrees. Rounded endpoints can sit slightly more than ``2r`` or less
    than ``2r`` apart, which moves the centre the browser picks; model that, not the
    ideal arc (SVG 1.1 implementation notes, F.6.5)."""
    if r <= 0 or p0 == p1:
        return [p0, p1]
    hx, hy = (p0[0] - p1[0]) / 2, (p0[1] - p1[1]) / 2
    half = math.hypot(hx, hy)
    r = max(r, half)
    coef = math.sqrt(max(0.0, r * r - half * half)) / half
    if large == sweep:
        coef = -coef
    # Centre = chord midpoint + coef * (the half chord rotated 90 degrees).
    cx = (p0[0] + p1[0]) / 2 + coef * hy
    cy = (p0[1] + p1[1]) / 2 - coef * hx
    a0 = math.atan2(p0[1] - cy, p0[0] - cx)
    da = math.atan2(p1[1] - cy, p1[0] - cx) - a0
    if sweep and da < 0:
        da += 2 * math.pi
    elif not sweep and da > 0:
        da -= 2 * math.pi
    n = max(2, math.ceil(abs(math.degrees(da)) / 5))
    pts = [
        (cx + r * math.cos(a0 + da * i / n), cy + r * math.sin(a0 + da * i / n))
        for i in range(n + 1)
    ]
    pts[0], pts[-1] = p0, p1
    return pts


class Layout:
    """Obstacles drawn so far + labels placed so far, for one figure."""

    def __init__(self, font_size: float) -> None:
        self.font_size = font_size
        self.strokes: list[tuple[tuple[float, float], tuple[float, float], float]] = []
        self.boxes: list[Box] = []

    def stroke(self, pts: Iterable[tuple[float, float]], width: float) -> None:
        """Record a drawn polyline (``width`` = its stroke width)."""
        seq = list(pts)
        for a, b in zip(seq, seq[1:], strict=False):
            self.strokes.append((a, b, width / 2))

    def box_at(
        self,
        x: float,
        y: float,
        text: str,
        anchor: str = "middle",
        size: float | None = None,
        vertical: bool = False,
    ) -> Box:
        """The estimated box of ``text`` drawn at baseline ``(x, y)``; ``vertical`` =
        turned -90 degrees about that point (reading upward, middle-anchored)."""
        w, asc, desc = text_size(text, size or self.font_size)
        if vertical:
            return (x - asc, y - w / 2, x + desc, y + w / 2)
        left = x - w / 2 if anchor == "middle" else x - w if anchor == "end" else x
        return (left, y - asc, left + w, y + desc)

    def hits(self, box: Box) -> int:
        """How many strokes and placed labels come within ``CLEAR`` of ``box``."""
        n = 0
        for a, b, hw in self.strokes:
            if _seg_near_box(a, b, box, hw + CLEAR):
                n += 1
        return n + sum(
            not (
                box[0] >= o[2] + CLEAR
                or o[0] >= box[2] + CLEAR
                or box[1] >= o[3] + CLEAR
                or o[1] >= box[3] + CLEAR
            )
            for o in self.boxes
        )

    def baseline(self, cx: float, cy: float, text: str, vertical: bool = False) -> tuple[int, int]:
        """Rounded middle-anchored baseline that centres ``text`` on ``(cx, cy)``."""
        _, asc, desc = text_size(text, self.font_size)
        if vertical:
            return math.floor(cx + (asc - desc) / 2 + 0.5), math.floor(cy + 0.5)
        return math.floor(cx + 0.5), math.floor(cy + (asc - desc) / 2 + 0.5)

    def best(
        self,
        text: str,
        centres: Iterable[tuple[float, float]],
        ok: Callable[[Box], bool] | None = None,
        vertical: bool = False,
    ) -> tuple[int, int, int]:
        """``(x, y, hits)``: the first candidate centre that is clear; failing that,
        the first that touches the fewest things. ``ok`` can rule a candidate out
        (counted as one more hit). Nothing is reserved."""
        best, best_hits = (0, 0), 1 << 30
        for cx, cy in centres:
            x, y = self.baseline(cx, cy, text, vertical)
            box = self.box_at(x, y, text, vertical=vertical)
            n = self.hits(box) + (0 if ok is None or ok(box) else 1)
            if n < best_hits:
                best, best_hits = (x, y), n
                if n == 0:
                    break
        return best[0], best[1], best_hits

    def place(
        self,
        text: str,
        centres: Iterable[tuple[float, float]],
        ok: Callable[[Box], bool] | None = None,
    ) -> tuple[int, int]:
        """:meth:`best`, then reserve the chosen box so later labels avoid it."""
        x, y, _ = self.best(text, centres, ok)
        self.reserve(x, y, text, "middle")
        return x, y

    def reserve(
        self,
        x: float,
        y: float,
        text: str,
        anchor: str = "start",
        size: float | None = None,
        vertical: bool = False,
    ) -> None:
        """Count a label placed by the caller (fixed position) as taken space."""
        self.boxes.append(self.box_at(x, y, text, anchor, size, vertical))

    def away(
        self,
        px: float,
        py: float,
        dirs: Iterable[tuple[float, float]],
        text: str,
        gap: float,
        steps: Iterable[float] = (0, 3, 6, 10, 15),
        vertical: bool = False,
    ) -> Iterator[tuple[float, float]]:
        """Centres that put ``text``'s box ``gap`` (+ each step) px from ``(px, py)``
        along each unit direction, for every direction in turn."""
        w, asc, desc = text_size(text, self.font_size)
        bw, bh = (asc + desc, w) if vertical else (w, asc + desc)
        step_list = list(steps)
        for ux, uy in dirs:
            reach = abs(ux) * bw / 2 + abs(uy) * bh / 2
            for k in step_list:
                d = gap + k + reach
                yield px + ux * d, py + uy * d

    def extent(self) -> Box | None:
        """Bounding box of every placed label."""
        if not self.boxes:
            return None
        return (
            min(b[0] for b in self.boxes),
            min(b[1] for b in self.boxes),
            max(b[2] for b in self.boxes),
            max(b[3] for b in self.boxes),
        )


def ring(prefer: tuple[float, float], step_deg: float = 15) -> list[tuple[float, float]]:
    """Unit directions all the way round, nearest to ``prefer`` first."""
    base = math.atan2(prefer[1], prefer[0])
    out = [(math.cos(base), math.sin(base))]
    k = 1
    while k * step_deg < 180 + 1e-9:
        for sign in (1, -1):
            a = base + sign * math.radians(k * step_deg)
            out.append((math.cos(a), math.sin(a)))
            if k * step_deg >= 180 - 1e-9:
                break
        k += 1
    return out


def widest_gap(
    dirs: list[tuple[float, float]], outward: tuple[float, float] = (0.0, 0.0)
) -> tuple[float, float] | None:
    """The unit direction in the middle of the widest empty sector between ``dirs``.
    Sectors of (nearly) equal width, such as either side of a straight line, are
    told apart by ``outward``: the one facing it wins."""
    if not dirs:
        return None
    angles = sorted(math.atan2(dy, dx) for dx, dy in dirs)
    best, best_mid = -math.inf, 0.0
    for i, a in enumerate(angles):
        nxt = angles[(i + 1) % len(angles)] + (2 * math.pi if i == len(angles) - 1 else 0)
        mid = (a + nxt) / 2
        score = nxt - a + 0.35 * (outward[0] * math.cos(mid) + outward[1] * math.sin(mid))
        if score > best + 1e-9:
            best, best_mid = score, mid
    return (math.cos(best_mid), math.sin(best_mid))
