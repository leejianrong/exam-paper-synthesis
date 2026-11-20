"""How a unit code prints (one place, so the paper, the key and the options agree).

The canonical unit codes stay ASCII (``"l"``, ``"ml"``, ``"cm^2"``: the schema enum, goldens and
saved papers are unchanged); print output uses the PSLE symbols, ``ℓ`` and ``mℓ``, and real
superscripts for area and volume, ``cm²`` and ``m³`` (EXA-142: no caret reaches a page).
The ``ℓ`` glyph
comes from a one-glyph Inter face (``assets/fonts/inter-ell-*.woff2``, cut from Inter's
latin-ext subset), so it is still the one typeface (EXA-94).
"""

from __future__ import annotations

PRINTED = {
    "l": "ℓ",
    "ml": "mℓ",
    "l/min": "ℓ/min",
    "cm^2": "cm²",
    "m^2": "m²",
    "cm^3": "cm³",
    "m^3": "m³",
}


def printed_unit(unit: str) -> str:
    """``"l"`` -> ``"ℓ"``, ``"cm^2"`` -> ``"cm²"`` and so on; every other code unchanged."""
    return PRINTED.get(unit, unit)
