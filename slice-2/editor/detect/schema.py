"""Esquema de detección por IA y mapeo a Coat. Sin red.

Los Literals replican el vocab curado (set blando del DSL). Un test
(test_detect_schema) garantiza que sean subconjunto del vocab — si vocab
cambia, hay que actualizar acá. Valores custom los entra el usuario en la
pantalla de confirmación (el DSL permite subtipo custom)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from indumentaria.dsl.assets import FlatRef
from indumentaria.dsl.components import Closure, Collar, Hem, Pocket, Sleeve
from indumentaria.dsl.garment import Coat
from indumentaria.dsl.measurements import POM, BodyProfile, Derivation, MeasurementSet

CollarSubtype = Literal["band", "camp", "notch_lapel", "peak_lapel", "point", "shawl", "spread"]
ClosureSubtype = Literal["double_breasted", "none", "single_breasted", "snap", "zip"]
SleeveSubtype = Literal["dropped", "raglan", "set_in"]
SleeveFit = Literal["regular", "slim", "wide_dropped"]
PocketSubtype = Literal["flap", "jet", "patch", "welt"]
PocketPlacement = Literal["chest", "hip", "side_seam"]
HemSubtype = Literal["curved", "straight", "vented"]


class DetectedCollar(BaseModel):
    subtype: CollarSubtype
    lapel_width_cm: float | None = None


class DetectedClosure(BaseModel):
    subtype: ClosureSubtype
    button_count: int = 0
    button_rows: int = 1


class DetectedSleeve(BaseModel):
    subtype: SleeveSubtype
    fit: SleeveFit = "regular"
    length: str = "long"


class DetectedPocket(BaseModel):
    subtype: PocketSubtype
    placement: PocketPlacement = "hip"
    count: int = 1


class DetectedHem(BaseModel):
    subtype: HemSubtype


class DetectedGarment(BaseModel):
    name: str
    silhouette: str
    collar: DetectedCollar | None = None
    closure: DetectedClosure | None = None
    sleeve: DetectedSleeve | None = None
    pockets: DetectedPocket | None = None
    hem: DetectedHem | None = None


def _placeholder_measurements() -> MeasurementSet:
    """PLACEHOLDER: medidas no reales. Setear las del usuario antes de un tech pack."""
    return MeasurementSet(
        body_profile=BodyProfile(
            measures={"chest_cm": 96.0, "waist_cm": 80.0, "shoulder_cm": 46.0,
                      "sleeve_length_cm": 64.0}
        ),
        poms=[
            POM(code="A", description="ancho de pecho", base_measurement=104.0,
                tol_plus=1.0, tol_minus=1.0,
                derivation=Derivation(body_measure="chest_cm", ease_cm=8.0)),
            POM(code="B", description="largo de manga", base_measurement=64.0,
                tol_plus=0.5, tol_minus=0.5),
        ],
    )


def to_coat(d: DetectedGarment, garment_id: str, flat_front: str,
            reference_image: str) -> Coat:
    """Mapea un DetectedGarment a un Coat. Puro (sin red). Los componentes ausentes se omiten."""
    components = []
    if d.collar:
        components.append(Collar(subtype=d.collar.subtype,
                                 lapel_width_cm=d.collar.lapel_width_cm))
    if d.closure:
        components.append(Closure(subtype=d.closure.subtype,
                                  button_count=d.closure.button_count,
                                  button_rows=d.closure.button_rows))
    if d.sleeve:
        components.append(Sleeve(subtype=d.sleeve.subtype, fit=d.sleeve.fit,
                                 length=d.sleeve.length))
    if d.pockets:
        components.append(Pocket(subtype=d.pockets.subtype,
                                 placement=d.pockets.placement,
                                 count=d.pockets.count))
    if d.hem:
        components.append(Hem(subtype=d.hem.subtype))
    return Coat(
        garment_id=garment_id, name=d.name, silhouette=d.silhouette,
        components=components, measurements=_placeholder_measurements(),
        flat=FlatRef(front=flat_front), reference_image=reference_image,
    )
