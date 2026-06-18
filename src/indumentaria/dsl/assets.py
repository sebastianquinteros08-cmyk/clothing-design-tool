"""Referencias a assets: flat SVG (front/back + anotaciones↔POM) y moldería.

El flat NO se dibuja desde el DSL (decisión A): se referencia el SVG del Slice 1.
La geometría de moldería se difiere a Slice 4 — PatternRef es solo un puntero.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Annotation(BaseModel):
    marker_id: str
    pom_code: str
    x: float
    y: float


class FlatRef(BaseModel):
    front: str
    back: str | None = None
    annotations: list[Annotation] = Field(default_factory=list)


class PatternRef(BaseModel):
    note: str | None = None
    path: str | None = None
