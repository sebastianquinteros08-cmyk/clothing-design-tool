from datetime import UTC, datetime

from editor.render.store import RenderRecord, RenderStore


def _rec(**kw) -> RenderRecord:
    base = dict(garment_id="g1", garment_version=1, fabric_id="lana_melton",
                color="navy", prompt="p", image_path="/renders/g1/x.png",
                model_id="fal-ai/test")
    base.update(kw)
    return RenderRecord(**base)


def test_add_and_get_roundtrip():
    store = RenderStore(":memory:")
    r = _rec()
    store.add(r)
    got = store.get(r.id)
    assert got is not None
    assert got.garment_id == "g1"
    assert got.model_id == "fal-ai/test"
    store.close()


def test_list_for_garment_newest_first():
    store = RenderStore(":memory:")
    older = _rec(created_at=datetime(2026, 1, 1, tzinfo=UTC))
    newer = _rec(created_at=datetime(2026, 6, 1, tzinfo=UTC))
    store.add(older)
    store.add(newer)
    ids = [r.id for r in store.list_for_garment("g1")]
    assert ids == [newer.id, older.id]
    assert store.list_for_garment("otra") == []
    store.close()
