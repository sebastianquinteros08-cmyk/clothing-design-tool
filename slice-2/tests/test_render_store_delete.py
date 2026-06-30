from editor.render.store import RenderRecord, RenderStore


def _rec(gid):
    return RenderRecord(garment_id=gid, garment_version=1, fabric_id="wool",
                        color="navy", prompt="p", image_path=f"/renders/{gid}/x.png",
                        model_id="m")


def test_delete_for_garment_removes_and_returns_paths():
    store = RenderStore(":memory:")
    store.add(_rec("g1"))
    store.add(_rec("g2"))
    paths = store.delete_for_garment("g1")
    assert paths == ["/renders/g1/x.png"]
    assert store.list_for_garment("g1") == []
    assert len(store.list_for_garment("g2")) == 1


def test_delete_for_garment_no_renders_returns_empty():
    store = RenderStore(":memory:")
    paths = store.delete_for_garment("nonexistent")
    assert paths == []
    assert store.list_for_garment("nonexistent") == []


def test_delete_for_garment_returns_all_paths():
    store = RenderStore(":memory:")
    store.add(RenderRecord(garment_id="g1", garment_version=1, fabric_id="wool",
                           color="navy", prompt="p1", image_path="/renders/g1/a.png",
                           model_id="m"))
    store.add(RenderRecord(garment_id="g1", garment_version=2, fabric_id="linen",
                           color="white", prompt="p2", image_path="/renders/g1/b.png",
                           model_id="m"))
    paths = store.delete_for_garment("g1")
    assert sorted(paths) == ["/renders/g1/a.png", "/renders/g1/b.png"]
    assert store.list_for_garment("g1") == []
