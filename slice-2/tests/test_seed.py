from editor.seed import SEED_GARMENT_ID, build_seed_peacoat, seed

from indumentaria.dsl.store import GarmentStore


def test_build_seed_peacoat_has_assets_and_four_poms():
    coat = build_seed_peacoat()
    assert coat.garment_id == SEED_GARMENT_ID
    assert coat.reference_image is not None
    assert {p.code for p in coat.measurements.poms} == {"A", "B", "C", "D"}
    assert len(coat.flat.annotations) == 4  # un marker por POM
    assert {a.pom_code for a in coat.flat.annotations} == {"A", "B", "C", "D"}


def test_seed_inserts_version_one():
    store = GarmentStore(":memory:")
    gid = seed(store)
    assert gid == SEED_GARMENT_ID
    assert store.get_head(gid).version == 1
    store.close()


def test_seed_is_idempotent():
    store = GarmentStore(":memory:")
    seed(store)
    seed(store)  # segunda vez no agrega versión
    assert store.get_head(SEED_GARMENT_ID).version == 1
    store.close()
