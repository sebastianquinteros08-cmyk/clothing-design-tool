"""Componentes tipados de la prenda. subtype = set blando (custom permitido).

`kind` es el discriminador que preserva el subtipo concreto en el round-trip JSON
(Pydantic reconstruye Collar/Closure/etc., no la base Component).
"""

from __future__ import annotations

from typing import Annotated, ClassVar, Literal, Union

from pydantic import BaseModel, Field, field_validator

from indumentaria.dsl import vocab


class Component(BaseModel):
    SUBTYPE_VOCAB: ClassVar[frozenset[str]] = frozenset()
    subtype: str
    notes: str | None = None

    @property
    def subtype_is_custom(self) -> bool:
        return vocab.is_custom(self.subtype, self.SUBTYPE_VOCAB)


class Collar(Component):
    SUBTYPE_VOCAB: ClassVar[frozenset[str]] = vocab.COLLAR_SUBTYPES
    kind: Literal["collar"] = "collar"
    lapel_width_cm: float | None = None

    @field_validator("lapel_width_cm")
    @classmethod
    def _width_positive(cls, v: float | None) -> float | None:
        if v is not None and v <= 0:
            raise ValueError("lapel_width_cm debe ser > 0")
        return v


class Closure(Component):
    SUBTYPE_VOCAB: ClassVar[frozenset[str]] = vocab.CLOSURE_SUBTYPES
    kind: Literal["closure"] = "closure"
    button_count: int = 0
    button_rows: int = 1

    @field_validator("button_count", "button_rows")
    @classmethod
    def _non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("conteo de botones/filas debe ser >= 0")
        return v


class Sleeve(Component):
    SUBTYPE_VOCAB: ClassVar[frozenset[str]] = vocab.SLEEVE_SUBTYPES
    kind: Literal["sleeve"] = "sleeve"
    fit: str = "regular"
    length: str = "long"


class Pocket(Component):
    SUBTYPE_VOCAB: ClassVar[frozenset[str]] = vocab.POCKET_SUBTYPES
    kind: Literal["pocket"] = "pocket"
    placement: str = "hip"
    count: int = 1

    @field_validator("count")
    @classmethod
    def _count_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("count debe ser >= 1")
        return v


class Hem(Component):
    SUBTYPE_VOCAB: ClassVar[frozenset[str]] = vocab.HEM_SUBTYPES
    kind: Literal["hem"] = "hem"


AnyComponent = Annotated[
    Union[Collar, Closure, Sleeve, Pocket, Hem],
    Field(discriminator="kind"),
]
