import pytest

from indumentaria.dsl.operations import CreateGarment, SetMeasurement


def test_create_garment_returns_copy(peacoat):
    op = CreateGarment(garment=peacoat)
    out = op.apply()
    assert out == peacoat
    assert out is not peacoat
    out.measurements.poms[0].base_measurement = 999.0
    assert peacoat.measurements.poms[0].base_measurement != 999.0


def test_set_measurement_updates_target_pom(peacoat):
    base = CreateGarment(garment=peacoat).apply()
    op = SetMeasurement(pom_code="A", base_measurement=110.0, tol_plus=2.0, tol_minus=2.0)
    out = op.apply(base)
    pom_a = next(p for p in out.measurements.poms if p.code == "A")
    assert pom_a.base_measurement == 110.0 and pom_a.tol_plus == 2.0 and pom_a.tol_minus == 2.0


def test_set_measurement_does_not_mutate_input(peacoat):
    base = CreateGarment(garment=peacoat).apply()
    original = next(p for p in base.measurements.poms if p.code == "A").base_measurement
    SetMeasurement(pom_code="A", base_measurement=110.0, tol_plus=1.0, tol_minus=1.0).apply(base)
    assert next(p for p in base.measurements.poms if p.code == "A").base_measurement == original


def test_set_measurement_unknown_pom_raises(peacoat):
    base = CreateGarment(garment=peacoat).apply()
    with pytest.raises(ValueError):
        op = SetMeasurement(pom_code="ZZ", base_measurement=10.0, tol_plus=0.0, tol_minus=0.0)
        op.apply(base)


def test_set_component_field_changes_subtype(peacoat):
    from indumentaria.dsl.operations import SetComponentField

    collar = next(c for c in peacoat.components if c.kind == "collar")
    op = SetComponentField(component_id=collar.component_id, field="subtype", value="peak_lapel")
    out = op.apply(peacoat)
    assert next(c for c in out.components if c.kind == "collar").subtype == "peak_lapel"
    # original intacto (apply es puro)
    assert next(c for c in peacoat.components if c.kind == "collar").subtype == "notch_lapel"


def test_set_component_field_revalidates(peacoat):
    import pytest
    from pydantic import ValidationError

    from indumentaria.dsl.operations import SetComponentField

    collar = next(c for c in peacoat.components if c.kind == "collar")
    bad = SetComponentField(component_id=collar.component_id, field="lapel_width_cm", value=-3.0)
    with pytest.raises(ValidationError):  # ValidationError de pydantic (lapel > 0)
        bad.apply(peacoat)


def test_set_component_field_unknown_id_raises(peacoat):
    import pytest

    from indumentaria.dsl.operations import SetComponentField

    op = SetComponentField(component_id="nope", field="subtype", value="x")
    with pytest.raises(ValueError):
        op.apply(peacoat)


def test_add_and_remove_component(peacoat):
    from indumentaria.dsl.components import Pocket
    from indumentaria.dsl.operations import AddComponent, RemoveComponent

    extra = Pocket(subtype="patch", placement="chest", count=1)
    added = AddComponent(component=extra).apply(peacoat)
    assert sum(1 for c in added.components if c.kind == "pocket") == 2

    removed = RemoveComponent(component_id=extra.component_id).apply(added)
    assert sum(1 for c in removed.components if c.kind == "pocket") == 1


def test_remove_unknown_component_raises(peacoat):
    import pytest

    from indumentaria.dsl.operations import RemoveComponent

    with pytest.raises(ValueError):
        RemoveComponent(component_id="nope").apply(peacoat)


def test_set_garment_field(peacoat):
    from indumentaria.dsl.operations import SetGarmentField

    out = SetGarmentField(field="name", value="Peacoat v2").apply(peacoat)
    assert out.name == "Peacoat v2"
    assert out.garment_type == "coat"  # sigue siendo Coat


def test_set_garment_field_rejects_non_editable(peacoat):
    import pytest

    from indumentaria.dsl.operations import SetGarmentField

    with pytest.raises(ValueError):
        SetGarmentField(field="garment_id", value="hack").apply(peacoat)


def test_restore_version_returns_snapshot(peacoat):
    from indumentaria.dsl.operations import RestoreVersion, SetGarmentField

    edited = SetGarmentField(field="name", value="cambiado").apply(peacoat)
    # restaurar al peacoat original
    op = RestoreVersion(target_version=1, snapshot=peacoat)
    out = op.apply(edited)
    assert out.name == "Navy Peacoat"
    assert out is not peacoat  # es una copia


def test_any_operation_discriminates():
    from pydantic import TypeAdapter

    from indumentaria.dsl.operations import AddComponent, AnyOperation

    payload = {"op_type": "add_component", "component": {"kind": "hem", "subtype": "curved"}}
    op = TypeAdapter(AnyOperation).validate_python(payload)
    assert isinstance(op, AddComponent)
