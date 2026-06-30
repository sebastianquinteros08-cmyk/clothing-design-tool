import pytest
from pydantic import ValidationError

from indumentaria.dsl.measurements import POM, BodyProfile, Derivation, MeasurementSet


def _body() -> BodyProfile:
    # PLACEHOLDER: setear medidas reales del usuario
    return BodyProfile(measures={"chest_cm": 96.0, "waist_cm": 80.0})


def test_body_rejects_out_of_range():
    with pytest.raises(ValidationError):
        BodyProfile(measures={"chest_cm": 1040.0})


def test_pom_base_out_of_range_rejected():
    with pytest.raises(ValidationError):
        POM(code="A", base_measurement=0.0)


def test_negative_tolerance_rejected():
    with pytest.raises(ValidationError):
        POM(code="A", base_measurement=104.0, tol_plus=-1.0)


def test_derived_base_computes_body_plus_ease():
    pom = POM(
        code="A",
        base_measurement=104.0,
        derivation=Derivation(body_measure="chest_cm", ease_cm=8.0),
    )
    assert pom.derived_base(_body()) == 104.0  # 96 + 8


def test_derived_base_none_without_derivation():
    assert POM(code="A", base_measurement=104.0).derived_base(_body()) is None


def test_duplicate_pom_codes_rejected():
    with pytest.raises(ValidationError):
        MeasurementSet(
            body_profile=_body(),
            poms=[POM(code="A", base_measurement=104.0), POM(code="A", base_measurement=64.0)],
        )


def test_derivation_must_reference_existing_body_measure():
    with pytest.raises(ValidationError):
        MeasurementSet(
            body_profile=_body(),
            poms=[
                POM(
                    code="A",
                    base_measurement=104.0,
                    derivation=Derivation(body_measure="inseam_cm", ease_cm=2.0),
                )
            ],
        )


def test_negative_tol_minus_rejected():
    with pytest.raises(ValidationError):
        POM(code="A", base_measurement=104.0, tol_minus=-1.0)


def test_derived_base_none_when_body_measure_absent():
    pom = POM(
        code="A",
        base_measurement=104.0,
        derivation=Derivation(body_measure="inseam_cm", ease_cm=2.0),
    )
    assert pom.derived_base(_body()) is None
