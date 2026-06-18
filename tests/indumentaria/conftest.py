import pytest

from indumentaria.dsl.assets import FlatRef
from indumentaria.dsl.components import Closure, Collar, Hem, Pocket, Sleeve
from indumentaria.dsl.garment import Coat
from indumentaria.dsl.materials import BOM, BOMRow
from indumentaria.dsl.measurements import BodyProfile, Derivation, MeasurementSet, POM


@pytest.fixture
def peacoat() -> Coat:
    # PLACEHOLDER: medidas corporales no reales — setear las del usuario (spec §Pendiente)
    body = BodyProfile(
        measures={"chest_cm": 96.0, "waist_cm": 80.0, "shoulder_cm": 46.0, "sleeve_length_cm": 64.0}
    )
    measurements = MeasurementSet(
        body_profile=body,
        poms=[
            POM(
                code="A",
                description="ancho de pecho 2,5 cm bajo sisa",
                base_measurement=104.0,
                tol_plus=1.0,
                tol_minus=1.0,
                derivation=Derivation(body_measure="chest_cm", ease_cm=8.0),
            ),
            POM(code="B", description="largo de manga", base_measurement=64.0,
                tol_plus=0.5, tol_minus=0.5),
        ],
    )
    return Coat(
        name="Peacoat Loewe",
        silhouette="oversized_cropped",
        components=[
            Collar(subtype="notch_lapel", lapel_width_cm=8.0),
            Closure(subtype="double_breasted", button_count=4, button_rows=2),
            Sleeve(subtype="set_in", fit="wide_dropped", length="long"),
            Pocket(subtype="welt", placement="hip", count=2),
            Hem(subtype="straight"),
        ],
        measurements=measurements,
        bom=BOM(
            rows=[
                BOMRow(category="Tela", description="100% lana", composition="100% wool",
                       gsm=450, pantone_code="19-4007 TCX"),
                BOMRow(category="Avío", description="botón corozo 24L", quantity=6),
            ]
        ),
        flat=FlatRef(front="slice-1/work/peacoat/flat.svg"),
    )
