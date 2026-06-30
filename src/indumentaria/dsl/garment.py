"""Garment: la prenda que compone componentes + medidas + BOM + assets.

`components` usa el discriminated union AnyComponent (preserva subtipos en JSON).
`load_garment` reconstruye la subclase correcta vía el registro GARMENT_TYPES
(soporta sumar Shirt/Pants lazy sin tocar el store).
"""

from __future__ import annotations

from typing import ClassVar
from uuid import uuid4

from pydantic import BaseModel, Field

from indumentaria.dsl.assets import FlatRef, PatternRef
from indumentaria.dsl.components import AnyComponent
from indumentaria.dsl.materials import BOM
from indumentaria.dsl.measurements import MeasurementSet


class Garment(BaseModel):
    garment_id: str = Field(default_factory=lambda: uuid4().hex)
    name: str
    garment_type: str = "garment"
    description: str = ""
    reference_image: str | None = None
    silhouette: str | None = None
    components: list[AnyComponent] = Field(default_factory=list)
    measurements: MeasurementSet
    bom: BOM = Field(default_factory=BOM)
    flat: FlatRef | None = None
    pattern: PatternRef | None = None


class Coat(Garment):
    garment_type: str = "coat"
    EXPECTED_SLOTS: ClassVar[tuple[str, ...]] = ("collar", "closure", "sleeve", "pocket", "hem")

    @property
    def missing_slots(self) -> list[str]:
        present = {c.kind for c in self.components}
        return [slot for slot in self.EXPECTED_SLOTS if slot not in present]


GARMENT_TYPES: dict[str, type[Garment]] = {"coat": Coat}


def load_garment(data: dict) -> Garment:
    """Reconstruye la subclase de Garment según data['garment_type']."""
    cls = GARMENT_TYPES.get(data.get("garment_type", ""), Garment)
    return cls.model_validate(data)
