"""Construye el prompt del render desde el DSL. Función pura, sin red.

El flat aporta la forma gruesa; este prompt aporta la semántica precisa del
diseño (subtipos + campos de cada componente) que el flat-silueta no muestra.
Presentación FIJA del MVP: producto sin cuerpo, flat-lay (prenda apoyada,
simétrica, sin cabeza ni maniquí). El on-body es un path futuro distinto
(try-on), no un parámetro de esta función.
"""

from __future__ import annotations

from editor.render.fabrics import Fabric
from indumentaria.dsl.garment import Garment


def _words(s: str | None) -> str:
    return (s or "").replace("_", " ").strip()


def _describe_component(c) -> str:  # noqa: ANN001 (AnyComponent union)
    kind = c.kind
    sub = _words(getattr(c, "subtype", ""))
    if kind == "collar":
        w = getattr(c, "lapel_width_cm", None)
        return f"{sub} collar" + (f" with {w}cm lapel" if w else "")
    if kind == "closure":
        bc = getattr(c, "button_count", None)
        br = getattr(c, "button_rows", None)
        extra = f" with exactly {bc} buttons total in {br} vertical columns" if bc and br else ""
        return f"{sub} closure{extra}"
    if kind == "sleeve":
        fit = _words(getattr(c, "fit", ""))
        length = _words(getattr(c, "length", ""))
        parts_s = [f"{sub} sleeves" if sub else "sleeves"]
        if fit:
            parts_s.append(f"{fit} fit")
        if length:
            parts_s.append(f"{length} length")
        return ", ".join(parts_s)
    if kind == "pocket":
        count = getattr(c, "count", None)
        placement = _words(getattr(c, "placement", ""))
        head = f"{count}x " if count else ""
        return (f"{head}{sub} pockets" + (f" at {placement}" if placement else "")).strip()
    if kind == "hem":
        return f"{sub} hem"
    return f"{sub} {kind}".strip()


def build_render_prompt(garment: Garment, fabric: Fabric, color: str) -> str:
    silhouette = _words(garment.silhouette)
    head = f"Photorealistic product flat-lay of a {silhouette} {garment.garment_type}".replace(
        "  ", " "
    )
    parts = [head.strip()]
    comp_phrases = [_describe_component(c) for c in garment.components]
    if comp_phrases:
        parts.append("with " + "; ".join(comp_phrases))
    parts.append(f"made of {color} {fabric.name} ({fabric.composition})")
    parts.append(
        "the garment laid flat and symmetric on a plain white background, no human body, "
        "no head, no mannequin, sleeves spread to show the silhouette, "
        "studio product photography, sharp focus, high detail"
    )
    return ", ".join(parts) + "."
