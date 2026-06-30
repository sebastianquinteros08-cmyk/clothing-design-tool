import pytest
from editor.service import EditorService, GarmentNotFound

from indumentaria.dsl.examples import build_peacoat
from indumentaria.dsl.operations import CreateGarment, SetGarmentField
from indumentaria.dsl.store import GarmentStore
from indumentaria.dsl.versioning import create_initial


@pytest.fixture
def service_with_peacoat():
    store = GarmentStore(":memory:")
    coat = build_peacoat()
    op = CreateGarment(garment=coat)
    store.save_version(create_initial(op), op)
    yield EditorService(store), coat.garment_id
    store.close()


def test_load_head_returns_version(service_with_peacoat):
    svc, gid = service_with_peacoat
    head = svc.load_head(gid)
    assert head.version == 1
    assert head.snapshot.name == "Navy Peacoat"


def test_apply_operation_creates_new_version(service_with_peacoat):
    svc, gid = service_with_peacoat
    v = svc.apply_operation(gid, SetGarmentField(field="name", value="Peacoat v2"))
    assert v.version == 2
    assert v.snapshot.name == "Peacoat v2"
    assert svc.load_head(gid).version == 2


def test_apply_operation_unknown_garment_raises():
    store = GarmentStore(":memory:")
    svc = EditorService(store)
    with pytest.raises(GarmentNotFound):
        svc.apply_operation("nope", SetGarmentField(field="name", value="x"))
    store.close()


def test_restore_creates_new_version_with_old_snapshot(service_with_peacoat):
    svc, gid = service_with_peacoat
    svc.apply_operation(gid, SetGarmentField(field="name", value="Peacoat v2"))  # v2
    restored = svc.restore(gid, target_version=1)  # v3 = snapshot de v1
    assert restored.version == 3
    assert restored.op_type == "restore_version"
    assert restored.snapshot.name == "Navy Peacoat"


def test_restore_unknown_version_raises(service_with_peacoat):
    svc, gid = service_with_peacoat
    with pytest.raises(ValueError):
        svc.restore(gid, target_version=99)
