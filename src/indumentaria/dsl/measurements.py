"""Modelo de medidas: body / ease / POM (híbrido C, single-talle).

POM.base_measurement es autoritativo (va al taller). `derivation` es opcional:
procedencia para mostrar/recalcular base = cuerpo + ease.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

MAX_CM = 300.0


class BodyProfile(BaseModel):
    """Medidas corporales del wearer, nombradas y extensibles (cm, en (0, MAX_CM]).

    PLACEHOLDER: los valores de ejemplo no son reales — setear las medidas
    reales del usuario antes de producir un tech pack (spec §Pendiente).
    """

    measures: dict[str, float] = Field(default_factory=dict)

    @field_validator("measures")
    @classmethod
    def _positive_sane(cls, v: dict[str, float]) -> dict[str, float]:
        for name, val in v.items():
            if not (0 < val <= MAX_CM):
                raise ValueError(f"medida {name}={val} fuera de rango (0, {MAX_CM}]")
        return v

    def get(self, name: str) -> float | None:
        return self.measures.get(name)


class Derivation(BaseModel):
    body_measure: str
    ease_cm: float


class POM(BaseModel):
    code: str
    description: str = ""
    base_measurement: float
    tol_plus: float = 0.0
    tol_minus: float = 0.0
    graded: dict[str, float] = Field(default_factory=dict)  # vacío: single-talle, diferido
    derivation: Derivation | None = None

    @field_validator("base_measurement")
    @classmethod
    def _base_sane(cls, v: float) -> float:
        if not (0 < v <= MAX_CM):
            raise ValueError(f"base_measurement={v} fuera de rango (0, {MAX_CM}]")
        return v

    @field_validator("tol_plus", "tol_minus")
    @classmethod
    def _tol_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("tolerancia debe ser >= 0")
        return v

    def derived_base(self, body: BodyProfile) -> float | None:
        """base recalculada = cuerpo + ease, o None si no hay derivación/medida."""
        if self.derivation is None:
            return None
        body_val = body.get(self.derivation.body_measure)
        if body_val is None:
            return None
        return body_val + self.derivation.ease_cm


class MeasurementSet(BaseModel):
    body_profile: BodyProfile
    poms: list[POM] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_codes_and_derivations(self) -> MeasurementSet:
        codes = [p.code for p in self.poms]
        if len(codes) != len(set(codes)):
            raise ValueError("códigos POM duplicados en el MeasurementSet")
        for p in self.poms:
            if p.derivation and p.derivation.body_measure not in self.body_profile.measures:
                raise ValueError(
                    f"POM {p.code}: derivation.body_measure "
                    f"'{p.derivation.body_measure}' no existe en el BodyProfile"
                )
        return self
