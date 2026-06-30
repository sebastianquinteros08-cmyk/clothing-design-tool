from indumentaria.dsl.examples import build_peacoat
from indumentaria.dsl.operations import CreateGarment
from indumentaria.dsl.store import GarmentStore
from indumentaria.dsl.versioning import create_initial


def _seed(store, name):
    coat = build_peacoat().model_copy(update={"garment_id": name, "name": name})
    op = CreateGarment(garment=coat)
    store.save_version(create_initial(op), op)
    return name


def test_list_garment_ids_returns_all():
    store = GarmentStore(":memory:")
    _seed(store, "a")
    _seed(store, "b")
    assert set(store.list_garment_ids()) == {"a", "b"}


def test_delete_garment_removes_it():
    store = GarmentStore(":memory:")
    _seed(store, "a")
    _seed(store, "b")
    store.delete_garment("a")
    assert store.list_garment_ids() == ["b"]
    assert store.get_head("a") is None
