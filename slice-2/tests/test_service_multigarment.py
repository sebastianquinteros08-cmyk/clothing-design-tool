import pytest
from editor.service import EditorService, GarmentNotFound

from indumentaria.dsl.examples import build_peacoat
from indumentaria.dsl.store import GarmentStore


def _svc():
    return EditorService(GarmentStore(":memory:"))


def test_create_garment_returns_id_and_is_loadable():
    svc = _svc()
    coat = build_peacoat().model_copy(update={"garment_id": "g1", "name": "Mía"})
    gid = svc.create_garment(coat)
    assert gid == "g1"
    head = svc.load_head("g1")
    assert head is not None and head.snapshot.name == "Mía"
    assert head.version == 1


def test_list_garments_summaries():
    svc = _svc()
    svc.create_garment(build_peacoat().model_copy(update={"garment_id": "g1", "name": "Uno"}))
    summaries = svc.list_garments()
    assert len(summaries) == 1
    s = summaries[0]
    assert s.garment_id == "g1" and s.name == "Uno" and s.garment_type == "coat"
    assert s.version == 1
    assert s.thumbnail_url == "slice-1/work/peacoat/flat.svg"


def test_list_garments_thumbnail_none_when_no_flat():
    svc = _svc()
    coat = build_peacoat().model_copy(update={"garment_id": "gnf", "name": "SinFlat", "flat": None})
    svc.create_garment(coat)
    s = next(x for x in svc.list_garments() if x.garment_id == "gnf")
    assert s.thumbnail_url is None


def test_delete_garment_missing_raises():
    svc = _svc()
    with pytest.raises(GarmentNotFound):
        svc.delete_garment("nope")
