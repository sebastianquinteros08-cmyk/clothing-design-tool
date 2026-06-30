import sqlite3

import pytest

from indumentaria.dsl.operations import CreateGarment, SetMeasurement
from indumentaria.dsl.store import GarmentStore
from indumentaria.dsl.versioning import apply, create_initial


def _seed(store, peacoat):
    create_op = CreateGarment(garment=peacoat)
    v1 = create_initial(create_op)
    store.save_version(v1, create_op)
    set_op = SetMeasurement(pom_code="A", base_measurement=110.0, tol_plus=1.0, tol_minus=1.0)
    v2 = apply(set_op, v1)
    store.save_version(v2, set_op)
    return v1, v2


def test_get_head_returns_latest_with_updated_value(tmp_path, peacoat):
    store = GarmentStore(tmp_path / "test.db")
    _v1, v2 = _seed(store, peacoat)
    head = store.get_head(peacoat.garment_id)
    assert head.version == 2
    pom_a = next(p for p in head.snapshot.measurements.poms if p.code == "A")
    assert pom_a.base_measurement == 110.0
    store.close()


def test_roundtrip_preserves_component_subtypes(tmp_path, peacoat):
    store = GarmentStore(tmp_path / "test.db")
    _seed(store, peacoat)
    head = store.get_head(peacoat.garment_id)
    collar = next(c for c in head.snapshot.components if c.kind == "collar")
    assert collar.lapel_width_cm == 8.0
    store.close()


def test_undo_via_prior_version_intact(tmp_path, peacoat):
    store = GarmentStore(tmp_path / "test.db")
    _seed(store, peacoat)
    v1 = store.get_version(peacoat.garment_id, 1)
    assert next(p for p in v1.snapshot.measurements.poms if p.code == "A").base_measurement == 104.0
    store.close()


def test_history_and_operations_log(tmp_path, peacoat):
    store = GarmentStore(tmp_path / "test.db")
    _seed(store, peacoat)
    assert [v.version for v in store.list_history(peacoat.garment_id)] == [1, 2]
    ops = store.get_operations(peacoat.garment_id)
    assert [o["type"] for o in ops] == ["create_garment", "set_measurement"]
    store.close()


def test_get_version_returns_specific_version(tmp_path, peacoat):
    store = GarmentStore(tmp_path / "test.db")
    _seed(store, peacoat)
    v2 = store.get_version(peacoat.garment_id, 2)
    assert v2.version == 2
    assert next(p for p in v2.snapshot.measurements.poms if p.code == "A").base_measurement == 110.0
    store.close()


def test_get_head_none_for_unknown_garment(tmp_path):
    store = GarmentStore(tmp_path / "test.db")
    assert store.get_head("does-not-exist") is None
    store.close()


def test_context_manager_closes(peacoat):
    from indumentaria.dsl.operations import CreateGarment
    from indumentaria.dsl.store import GarmentStore
    from indumentaria.dsl.versioning import create_initial

    with GarmentStore(":memory:") as store:
        v1 = create_initial(CreateGarment(garment=peacoat))
        store.save_version(v1, CreateGarment(garment=peacoat))
        assert store.get_head(peacoat.garment_id).version == 1

    # Verify connection is actually closed after __exit__
    with pytest.raises(sqlite3.ProgrammingError):
        store.get_head(peacoat.garment_id)


def test_get_operations_created_at_is_datetime(peacoat):
    from datetime import datetime

    from indumentaria.dsl.operations import CreateGarment
    from indumentaria.dsl.store import GarmentStore
    from indumentaria.dsl.versioning import create_initial

    with GarmentStore(":memory:") as store:
        op = CreateGarment(garment=peacoat)
        store.save_version(create_initial(op), op)
        ops = store.get_operations(peacoat.garment_id)
        assert isinstance(ops[0]["created_at"], datetime)


def test_save_version_rejects_mismatched_op_type(peacoat):
    from indumentaria.dsl.operations import CreateGarment, SetMeasurement
    from indumentaria.dsl.store import GarmentStore
    from indumentaria.dsl.versioning import create_initial

    with GarmentStore(":memory:") as store:
        version = create_initial(CreateGarment(garment=peacoat))  # op_type = create_garment
        wrong = SetMeasurement(pom_code="A", base_measurement=1.0, tol_plus=0, tol_minus=0)
        with pytest.raises(ValueError):
            store.save_version(version, wrong)  # set_measurement != create_garment
