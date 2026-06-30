import editor.main as main
import pytest
from editor.seed import SEED_GARMENT_ID, seed
from editor.service import EditorService
from fastapi.testclient import TestClient

from indumentaria.dsl.store import GarmentStore


@pytest.fixture
def client():
    store = GarmentStore(":memory:")
    seed(store)
    main.service = EditorService(store)  # inyectar store en memoria
    with TestClient(main.app) as c:
        yield c
    store.close()


def test_get_garment_head(client):
    r = client.get(f"/api/garment/{SEED_GARMENT_ID}")
    assert r.status_code == 200
    body = r.json()
    assert body["version"] == 1
    assert body["garment"]["name"] == "Navy Peacoat"


def test_get_garment_404(client):
    assert client.get("/api/garment/nope").status_code == 404


def test_post_op_sets_garment_field(client):
    r = client.post(
        f"/api/garment/{SEED_GARMENT_ID}/op",
        json={"op": {"op_type": "set_garment_field", "field": "name", "value": "Nuevo"}},
    )
    assert r.status_code == 200
    assert r.json()["version"] == 2
    assert r.json()["garment"]["name"] == "Nuevo"


def test_post_op_invalid_value_returns_400(client):
    gid = SEED_GARMENT_ID
    collar_id = next(c["component_id"] for c in client.get(f"/api/garment/{gid}").json()
                     ["garment"]["components"] if c["kind"] == "collar")
    r = client.post(
        f"/api/garment/{gid}/op",
        json={"op": {"op_type": "set_component_field", "component_id": collar_id,
                     "field": "lapel_width_cm", "value": -5}},
    )
    assert r.status_code == 400


def test_restore_endpoint(client):
    gid = SEED_GARMENT_ID
    client.post(f"/api/garment/{gid}/op",
                json={"op": {"op_type": "set_garment_field", "field": "name", "value": "X"}})
    r = client.post(f"/api/garment/{gid}/restore", json={"target_version": 1})
    assert r.status_code == 200
    assert r.json()["garment"]["name"] == "Navy Peacoat"
    assert r.json()["version"] == 3


def test_history_endpoint(client):
    r = client.get(f"/api/garment/{SEED_GARMENT_ID}/history")
    assert r.status_code == 200
    assert r.json()[0]["op_type"] == "create_garment"


def test_vocab_endpoint(client):
    body = client.get("/api/vocab").json()
    assert "notch_lapel" in body["collar"]
    assert "double_breasted" in body["closure"]
