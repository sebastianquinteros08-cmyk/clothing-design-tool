"""BOM: una sola lista categorizada (tela + avíos + labels + packing).

Modelo del research §3.3. `category` = set blando (custom permitido).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from indumentaria.dsl import vocab


class BOMRow(BaseModel):
    category: str
    description: str
    composition: str | None = None
    gsm: int | None = None
    color_name: str | None = None
    pantone_code: str | None = None
    quantity: float | None = None
    placement: str | None = None
    supplier: str | None = None
    supplier_ref: str | None = None
    cost: float | None = None

    @property
    def category_is_custom(self) -> bool:
        return vocab.is_custom(self.category, vocab.BOM_CATEGORIES)


class BOM(BaseModel):
    rows: list[BOMRow] = Field(default_factory=list)
