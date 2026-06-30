"""Operaciones tipadas. apply() es PURO: devuelve una prenda nueva, no muta.

Ops de edición que arma el cliente (unidas en AnyOperation): SetMeasurement,
SetComponentField, AddComponent, RemoveComponent, SetGarmentField. Más CreateGarment
(seed) y RestoreVersion (undo/restore; la arma el backend, no va en AnyOperation).
La taxonomía sigue creciendo lazy (D6) a medida que el editor genere ediciones nuevas.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from indumentaria.dsl.components import AnyComponent
from indumentaria.dsl.garment import Garment, load_garment


class Operation(BaseModel):
    op_type: str

    def apply(self, garment: Garment) -> Garment:
        raise NotImplementedError


class CreateGarment(Operation):
    op_type: Literal["create_garment"] = "create_garment"
    garment: Garment

    def apply(self, garment: Garment | None = None) -> Garment:
        return self.garment.model_copy(deep=True)


class SetMeasurement(Operation):
    op_type: Literal["set_measurement"] = "set_measurement"
    pom_code: str
    base_measurement: float
    tol_plus: float
    tol_minus: float

    def apply(self, garment: Garment) -> Garment:
        new = garment.model_copy(deep=True)
        for pom in new.measurements.poms:
            if pom.code == self.pom_code:
                pom.base_measurement = self.base_measurement
                pom.tol_plus = self.tol_plus
                pom.tol_minus = self.tol_minus
                return new
        raise ValueError(f"POM '{self.pom_code}' no existe en la prenda")


_EDITABLE_GARMENT_FIELDS = frozenset({"name", "description", "silhouette"})


class SetComponentField(Operation):
    op_type: Literal["set_component_field"] = "set_component_field"
    component_id: str
    field: str
    value: Any

    def apply(self, garment: Garment) -> Garment:
        new = garment.model_copy(deep=True)
        for i, comp in enumerate(new.components):
            if comp.component_id == self.component_id:
                if self.field in ("kind", "component_id"):
                    raise ValueError(f"campo '{self.field}' no es editable")
                if self.field not in type(comp).model_fields:
                    raise ValueError(f"campo '{self.field}' no existe en {type(comp).__name__}")
                data = comp.model_dump()
                data[self.field] = self.value
                new.components[i] = type(comp).model_validate(data)  # re-valida
                return new
        raise ValueError(f"componente '{self.component_id}' no existe")


class AddComponent(Operation):
    op_type: Literal["add_component"] = "add_component"
    component: AnyComponent

    def apply(self, garment: Garment) -> Garment:
        new = garment.model_copy(deep=True)
        new.components.append(self.component.model_copy(deep=True))
        return new


class RemoveComponent(Operation):
    op_type: Literal["remove_component"] = "remove_component"
    component_id: str

    def apply(self, garment: Garment) -> Garment:
        new = garment.model_copy(deep=True)
        kept = [c for c in new.components if c.component_id != self.component_id]
        if len(kept) == len(new.components):
            raise ValueError(f"componente '{self.component_id}' no existe")
        new.components = kept
        return new


class SetGarmentField(Operation):
    op_type: Literal["set_garment_field"] = "set_garment_field"
    field: str
    value: Any

    def apply(self, garment: Garment) -> Garment:
        if self.field not in _EDITABLE_GARMENT_FIELDS:
            raise ValueError(f"campo de prenda '{self.field}' no es editable")
        data = garment.model_dump()
        data[self.field] = self.value
        return load_garment(data)  # reconstruye la subclase + valida


class RestoreVersion(Operation):
    op_type: Literal["restore_version"] = "restore_version"
    target_version: int
    snapshot: Garment

    def apply(self, garment: Garment | None = None) -> Garment:
        return self.snapshot.model_copy(deep=True)


AnyOperation = Annotated[
    SetMeasurement | SetComponentField | AddComponent | RemoveComponent | SetGarmentField,
    Field(discriminator="op_type"),
]
