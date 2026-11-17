"""Label-collision check for rendered SVG figures (EXA-136; not a test module).

Real papers keep a figure's text clear of its lines: side lengths sit outside the
edge, angle values inside the arc, vertex letters outside the corner. This helper
reads an SVG the engine drew, estimates each ``<text>``'s box from its font size
and characters (an approximate Inter glyph width per character), and reports:

* a label that touches any stroke the figure draws (lines, polylines, polygons,
  rect and circle outlines, and path segments including arcs and curves),
* two labels that overlap,
* a label that falls outside the viewBox.

It deliberately knows nothing about how a renderer placed its labels: it only
parses the markup, so it is an independent check of the drawing.
"""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

_NS = "{http://www.w3.org/2000/svg}"

# Approximate Inter advance widths, in ems. Unknown glyphs fall back to the
# class default (digit / upper / lower / other).
_WIDE = {"m": 0.86, "w": 0.78, "M": 0.88, "W": 0.98, "%": 0.86, "@": 0.95}
_NARROW = {
    "i": 0.25,
    "l": 0.25,
    "j": 0.25,
    "I": 0.28,
    "t": 0.36,
    "f": 0.36,
    "r": 0.38,
    " ": 0.27,
    ".": 0.27,
    ",": 0.27,
    ":": 0.27,
    "'": 0.24,
    "(": 0.36,
    ")": 0.36,
    "°": 0.42,
    "-": 0.42,
    "1": 0.45,
    "ℓ": 0.45,
}
_DESCENDERS = set("gjpqy(),")

# Extra air (px) a label must keep from a stroke and from another label.
CLEARANCE = 1.0


def glyph_width(ch: str) -> float:
    if ch in _WIDE:
        return _WIDE[ch]
    if ch in _NARROW:
        return _NARROW[ch]
    if ch.isdigit():
        return 0.62
    if ch.isupper():
        return 0.68
    if ch.islower():
        return 0.56
    return 0.62


def text_width(text: str, size: float, bold: bool = False) -> float:
    return sum(glyph_width(c) for c in text) * size * (1.06 if bold else 1.0)


@dataclass(frozen=True)
class Box:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float

    def overlaps(self, other: Box, gap: float = 0.0) -> bool:
        return (
            self.x0 < other.x1 + gap
            and other.x0 < self.x1 + gap
            and self.y0 < other.y1 + gap
            and other.y0 < self.y1 + gap
        )


@dataclass(frozen=True)
class Stroke:
    kind: str
    a: tuple[float, float]
    b: tuple[float, float]
    width: float


@dataclass
class _Ctx:
    dx: float = 0.0
    dy: float = 0.0
    font_size: float = 16.0
    anchor: str = "start"
    bold: bool = False
    stroke: str | None = None
    stroke_width: float = 1.0


def _num(v: str | None, default: float = 0.0) -> float:
    if v is None:
        return default
    m = re.match(r"\s*(-?[\d.]+(?:e-?\d+)?)", v)
    return float(m.group(1)) if m else default


def _child_ctx(el: ET.Element, ctx: _Ctx) -> _Ctx:
    c = _Ctx(**ctx.__dict__)
    if el.get("font-size"):
        c.font_size = _num(el.get("font-size"))
    if el.get("text-anchor"):
        c.anchor = el.get("text-anchor") or "start"
    fw = el.get("font-weight")
    if fw:
        c.bold = fw in ("bold", "600", "700", "800", "900")
    if el.get("stroke"):
        c.stroke = el.get("stroke")
    if el.get("stroke-width"):
        c.stroke_width = _num(el.get("stroke-width"), 1.0)
    tr = el.get("transform")
    if tr and el.tag != _NS + "text":
        m = re.match(r"\s*translate\(\s*(-?[\d.]+)[ ,]+(-?[\d.]+)\s*\)\s*$", tr)
        assert m, f"unsupported group transform {tr!r}"
        c.dx += float(m.group(1))
        c.dy += float(m.group(2))
    return c


def _points(attr: str) -> list[tuple[float, float]]:
    nums = [float(n) for n in re.findall(r"-?[\d.]+(?:e-?\d+)?", attr)]
    return list(zip(nums[0::2], nums[1::2], strict=True))


def _arc_points(
    p0: tuple[float, float],
    rx: float,
    ry: float,
    phi_deg: float,
    large: int,
    sweep: int,
    p1: tuple[float, float],
) -> list[tuple[float, float]]:
    """Sample an SVG elliptical arc (endpoint parameterisation, SVG spec F.6.5)."""
    if rx == 0 or ry == 0 or p0 == p1:
        return [p0, p1]
    phi = math.radians(phi_deg)
    cos_p, sin_p = math.cos(phi), math.sin(phi)
    x1p = cos_p * (p0[0] - p1[0]) / 2 + sin_p * (p0[1] - p1[1]) / 2
    y1p = -sin_p * (p0[0] - p1[0]) / 2 + cos_p * (p0[1] - p1[1]) / 2
    rx, ry = abs(rx), abs(ry)
    lam = (x1p / rx) ** 2 + (y1p / ry) ** 2
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    coef = math.sqrt(max(0.0, num / den)) if den else 0.0
    if large == sweep:
        coef = -coef
    cxp, cyp = coef * rx * y1p / ry, -coef * ry * x1p / rx
    cx = cos_p * cxp - sin_p * cyp + (p0[0] + p1[0]) / 2
    cy = sin_p * cxp + cos_p * cyp + (p0[1] + p1[1]) / 2

    def ang(ux: float, uy: float, vx: float, vy: float) -> float:
        a = math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
        return a

    t1 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dt = ang((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not sweep and dt > 0:
        dt -= 2 * math.pi
    elif sweep and dt < 0:
        dt += 2 * math.pi
    n = max(4, int(abs(dt) / (math.pi / 36)))
    pts = []
    for i in range(n + 1):
        t = t1 + dt * i / n
        x = rx * math.cos(t)
        y = ry * math.sin(t)
        pts.append((cos_p * x - sin_p * y + cx, sin_p * x + cos_p * y + cy))
    pts[0], pts[-1] = p0, p1
    return pts


def _path_polylines(d: str) -> list[list[tuple[float, float]]]:
    toks = re.findall(r"[MmLlHhVvAaZzCcQq]|-?[\d.]+(?:e-?\d+)?", d)
    out: list[list[tuple[float, float]]] = []
    cur: list[tuple[float, float]] = []
    pos = (0.0, 0.0)
    start = pos
    i = 0
    cmd = ""

    def take(n: int) -> list[float]:
        nonlocal i
        vals = [float(t) for t in toks[i : i + n]]
        i += n
        return vals

    while i < len(toks):
        if re.match(r"[A-Za-z]", toks[i]):
            cmd = toks[i]
            i += 1
            if cmd in "Zz":
                cur.append(start)
                out.append(cur)
                cur = [start]
                pos = start
                continue
        rel = cmd.islower()
        c = cmd.upper()
        ox, oy = pos if rel else (0.0, 0.0)
        if c == "M":
            x, y = take(2)
            pos = (ox + x, oy + y)
            if len(cur) > 1:
                out.append(cur)
            cur = [pos]
            start = pos
            cmd = "l" if rel else "L"
        elif c == "L":
            x, y = take(2)
            pos = (ox + x, oy + y)
            cur.append(pos)
        elif c == "H":
            (x,) = take(1)
            pos = (x + (pos[0] if rel else 0.0), pos[1])
            cur.append(pos)
        elif c == "V":
            (y,) = take(1)
            pos = (pos[0], y + (pos[1] if rel else 0.0))
            cur.append(pos)
        elif c == "A":
            rx, ry, phi, large, sweep, x, y = take(7)
            end = (ox + x, oy + y)
            cur.extend(_arc_points(pos, rx, ry, phi, int(large), int(sweep), end)[1:])
            pos = end
        elif c in "CQ":
            n = 6 if c == "C" else 4
            vals = take(n)
            ctrl = [(ox + vals[k], oy + vals[k + 1]) for k in range(0, n, 2)]
            pts = [pos, *ctrl]
            for s in range(1, 13):
                t = s / 12
                layer = pts
                while len(layer) > 1:
                    layer = [
                        (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
                        for a, b in zip(layer, layer[1:], strict=False)
                    ]
                cur.append(layer[0])
            pos = pts[-1]
        else:  # pragma: no cover - renderer emits only the commands above
            raise AssertionError(f"unsupported path command {cmd!r}")
    if len(cur) > 1:
        out.append(cur)
    return out


def _text_box(el: ET.Element, ctx: _Ctx) -> Box | None:
    text = "".join(el.itertext()).strip()
    if not text:
        return None
    size, bold = ctx.font_size, ctx.bold
    w = text_width(text, size, bold)
    asc = 0.75 * size
    desc = (0.22 if set(text) & _DESCENDERS else 0.04) * size
    x, y = _num(el.get("x")), _num(el.get("y"))
    rot = 0.0
    tr = el.get("transform")
    if tr:
        m = re.search(r"translate\(\s*(-?[\d.]+)[ ,]+(-?[\d.]+)\s*\)", tr)
        if m:
            x, y = x + float(m.group(1)), y + float(m.group(2))
        r = re.search(r"rotate\(\s*(-?[\d.]+)", tr)
        if r:
            rot = float(r.group(1))
    if ctx.anchor == "middle":
        left = -w / 2
    elif ctx.anchor == "end":
        left = -w
    else:
        left = 0.0
    corners = [(left, -asc), (left + w, -asc), (left, desc), (left + w, desc)]
    if rot:
        a = math.radians(rot)
        corners = [
            (cx * math.cos(a) - cy * math.sin(a), cx * math.sin(a) + cy * math.cos(a))
            for cx, cy in corners
        ]
    xs = [x + ctx.dx + c[0] for c in corners]
    ys = [y + ctx.dy + c[1] for c in corners]
    return Box(text, min(xs), min(ys), max(xs), max(ys))


@dataclass
class Figure:
    viewbox: tuple[float, float, float, float]
    labels: list[Box]
    strokes: list[Stroke]


def parse(svg: str) -> Figure:
    root = ET.fromstring(svg)
    vb = [float(v) for v in (root.get("viewBox") or "0 0 0 0").split()]
    labels: list[Box] = []
    strokes: list[Stroke] = []

    def add(kind: str, pts: list[tuple[float, float]], ctx: _Ctx) -> None:
        for a, b in zip(pts, pts[1:], strict=False):
            pa, pb = (a[0] + ctx.dx, a[1] + ctx.dy), (b[0] + ctx.dx, b[1] + ctx.dy)
            if pa != pb:
                strokes.append(Stroke(kind, pa, pb, ctx.stroke_width))

    def walk(el: ET.Element, ctx: _Ctx, nested: bool) -> None:
        tag = el.tag.replace(_NS, "")
        if tag == "svg" and nested:
            ctx = _Ctx(**ctx.__dict__)
            ctx.dx += _num(el.get("x"))
            ctx.dy += _num(el.get("y"))
        c = _child_ctx(el, ctx)
        stroked = c.stroke not in (None, "none") and c.stroke_width > 0
        if tag == "text":
            box = _text_box(el, c)
            if box:
                labels.append(box)
            return
        if stroked:
            g = el.get
            if tag == "line":
                p = [(_num(g("x1")), _num(g("y1"))), (_num(g("x2")), _num(g("y2")))]
                add("line", p, c)
            elif tag in ("polyline", "polygon"):
                pts = _points(g("points") or "")
                if tag == "polygon" and pts:
                    pts.append(pts[0])
                add(tag, pts, c)
            elif tag == "rect":
                x, y = _num(g("x")), _num(g("y"))
                w, h = _num(g("width")), _num(g("height"))
                add("rect", [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)], c)
            elif tag == "circle":
                cx, cy, r = _num(g("cx")), _num(g("cy")), _num(g("r"))
                pts = [
                    (cx + r * math.cos(t * math.pi / 36), cy + r * math.sin(t * math.pi / 36))
                    for t in range(73)
                ]
                add("circle", pts, c)
            elif tag == "path":
                for poly in _path_polylines(g("d") or ""):
                    add("path", poly, c)
        for child in el:
            walk(child, c, True)

    walk(root, _Ctx(), False)
    return Figure((vb[0], vb[1], vb[2], vb[3]), labels, strokes)


def _seg_box_distance(a: tuple[float, float], b: tuple[float, float], box: Box) -> float:
    """Distance from segment ab to an axis-aligned box (0 when they intersect)."""
    # Clip the segment to the box (Liang-Barsky): any overlap means distance 0.
    dx, dy = b[0] - a[0], b[1] - a[1]
    t0, t1 = 0.0, 1.0
    hit = True
    for p, q in (
        (-dx, a[0] - box.x0),
        (dx, box.x1 - a[0]),
        (-dy, a[1] - box.y0),
        (dy, box.y1 - a[1]),
    ):
        if p == 0:
            if q < 0:
                hit = False
                break
        else:
            t = q / p
            if p < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
    if hit and t0 <= t1:
        return 0.0

    def pt_seg(px: float, py: float) -> float:
        L = dx * dx + dy * dy
        t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - a[0]) * dx + (py - a[1]) * dy) / L))
        return math.hypot(a[0] + t * dx - px, a[1] + t * dy - py)

    def pt_box(px: float, py: float) -> float:
        ex = max(box.x0 - px, 0.0, px - box.x1)
        ey = max(box.y0 - py, 0.0, py - box.y1)
        return math.hypot(ex, ey)

    corners = [(box.x0, box.y0), (box.x1, box.y0), (box.x0, box.y1), (box.x1, box.y1)]
    return min([pt_seg(*c) for c in corners] + [pt_box(*a), pt_box(*b)])


def collisions(svg: str, clearance: float = CLEARANCE) -> list[str]:
    """Every label/stroke, label/label and label/viewBox problem in ``svg``."""
    fig = parse(svg)
    vx, vy, vw, vh = fig.viewbox
    problems: list[str] = []
    for box in fig.labels:
        if box.x0 < vx or box.y0 < vy or box.x1 > vx + vw or box.y1 > vy + vh:
            problems.append(f"label {box.text!r} leaves the viewBox {fig.viewbox}: {box}")
        for s in fig.strokes:
            if _seg_box_distance(s.a, s.b, box) < s.width / 2 + clearance:
                problems.append(f"label {box.text!r} touches a {s.kind} {s.a}->{s.b}")
                break
    for i, a in enumerate(fig.labels):
        for b in fig.labels[i + 1 :]:
            if a.overlaps(b, clearance):
                problems.append(f"labels {a.text!r} and {b.text!r} overlap")
    return problems
