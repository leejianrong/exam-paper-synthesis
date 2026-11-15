"""How a unit code prints (one place, so the paper, the key and the options agree).

The canonical unit codes stay ASCII (``"l"``, ``"ml"``: the schema enum, goldens and saved
papers are unchanged); print output uses the PSLE symbols, ``ℓ`` and ``mℓ``. The ``ℓ`` glyph
comes from a one-glyph Inter face (``assets/fonts/inter-ell-*.woff2``, cut from Inter's
latin-ext subset), so it is still the one typeface (EXA-94).
"""

from __future__ import annotations

PRINTED = {"l": "ℓ", "ml": "mℓ"}


def printed_unit(unit: str) -> str:
    """``"l"`` -> ``"ℓ"``, ``"ml"`` -> ``"mℓ"``; every other code unchanged."""
    return PRINTED.get(unit, unit)
