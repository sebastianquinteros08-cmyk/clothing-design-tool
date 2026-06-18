"""Vocabularios curados de subtipos y categorías (set blando).

Alimentan los dropdowns del editor (Slice 2b) y la validación blanda:
un valor fuera del set se acepta igual, marcado como custom.
"""

from __future__ import annotations

COLLAR_SUBTYPES = frozenset(
    {"notch_lapel", "peak_lapel", "shawl", "band", "spread", "point", "camp"}
)
CLOSURE_SUBTYPES = frozenset({"double_breasted", "single_breasted", "zip", "snap", "none"})
SLEEVE_SUBTYPES = frozenset({"set_in", "raglan", "dropped"})
SLEEVE_FITS = frozenset({"slim", "regular", "wide_dropped"})
POCKET_SUBTYPES = frozenset({"welt", "patch", "flap", "jet"})
POCKET_PLACEMENTS = frozenset({"hip", "chest", "side_seam"})
HEM_SUBTYPES = frozenset({"straight", "curved", "vented"})
BOM_CATEGORIES = frozenset({"Style", "Tela", "Avío", "Label", "Packing"})


def is_custom(value: str, vocab: frozenset[str]) -> bool:
    """True si `value` no está en el set curado (valor custom, permitido)."""
    return value not in vocab
