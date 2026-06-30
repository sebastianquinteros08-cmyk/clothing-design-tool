"""Siembra el navy peacoat como prenda editable (versión 1) en el store.

Coordenadas de annotations en fracción [0,1] del flat mostrado (afinadas por el
paso de verificación E2E).
"""

from __future__ import annotations

from indumentaria.dsl.assets import Annotation, FlatRef
from indumentaria.dsl.examples import build_peacoat
from indumentaria.dsl.garment import Coat
from indumentaria.dsl.measurements import POM, Derivation
from indumentaria.dsl.operations import CreateGarment
from indumentaria.dsl.store import GarmentStore
from indumentaria.dsl.versioning import create_initial

SEED_GARMENT_ID = "peacoat-seed"


def build_seed_peacoat() -> Coat:
    base = build_peacoat()
    poms = [
        *base.measurements.poms,  # A (pecho), B (manga)
        POM(code="C", description="ancho de hombro", base_measurement=48.0,
            tol_plus=0.5, tol_minus=0.5,
            derivation=Derivation(body_measure="shoulder_cm", ease_cm=2.0)),
        POM(code="D", description="largo de cuerpo (HPS a ruedo)", base_measurement=72.0,
            tol_plus=1.0, tol_minus=1.0),
    ]
    flat = FlatRef(
        front="/assets/peacoat/flat.svg",
        # coords en fracción [0,1] del flat; aproximadas, ajustables a ojo — solo ayuda visual.
        annotations=[
            Annotation(marker_id="m_A", pom_code="A", x=0.50, y=0.43),  # ancho de pecho (bajo sisa)
            Annotation(marker_id="m_B", pom_code="B", x=0.20, y=0.66),  # largo de manga (puño izq)
            Annotation(marker_id="m_C", pom_code="C", x=0.50, y=0.34),  # ancho de hombro
            Annotation(marker_id="m_D", pom_code="D", x=0.50, y=0.84),  # largo de cuerpo (ruedo)
        ],
    )
    measurements = base.measurements.model_copy(update={"poms": poms})
    return base.model_copy(update={
        "garment_id": SEED_GARMENT_ID,
        "reference_image": "/assets/peacoat/reference.jpg",
        "flat": flat,
        "measurements": measurements,
    })


def seed(store: GarmentStore) -> str:
    if store.get_head(SEED_GARMENT_ID) is not None:
        return SEED_GARMENT_ID  # ya sembrado
    coat = build_seed_peacoat()
    op = CreateGarment(garment=coat)
    store.save_version(create_initial(op), op)
    return SEED_GARMENT_ID
