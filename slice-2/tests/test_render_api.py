import base64

import editor.main as main
import pytest
from editor.render.backend import FakeRenderer
from editor.render.service import RenderService
from editor.render.store import RenderStore
from editor.seed import SEED_GARMENT_ID, seed
from editor.service import EditorService
from fastapi.testclient import TestClient

from indumentaria.dsl.store import GarmentStore

_DATAURL = "data:image/png;base64," + base64.b64encode(b"flatpng").decode()


@pytest.fixture
def client(tmp_path):
    gstore = GarmentStore(":memory:")
    seed(gstore)
    rstore = RenderStore(":memory:")
    main.service = EditorService(gstore)
    main.render_service = RenderService(
        gstore, rstore, FakeRenderer(model_id="fake"),
        assets_dir=tmp_path / "assets", renders_dir=tmp_path / "renders")
    with TestClient(main.app) as c:
        yield c
    gstore.close()
    rstore.close()


def test_get_fabrics(client):
    body = client.get("/api/fabrics").json()
    ids = {f["id"] for f in body}
    assert "lana_melton" in ids
    assert body[0]["swatch_url"].startswith("/assets/fabrics/")


def test_post_render_returns_record(client):
    r = client.post(f"/api/garment/{SEED_GARMENT_ID}/render",
                    json={"fabric_id": "lana_melton", "flat_png": _DATAURL})
    assert r.status_code == 200
    body = r.json()
    assert body["fabric_id"] == "lana_melton"
    assert body["color"] == "navy"
    assert body["image_path"].startswith(f"/renders/{SEED_GARMENT_ID}/")


def test_post_render_unknown_garment_404(client):
    r = client.post("/api/garment/nope/render",
                    json={"fabric_id": "denim", "flat_png": _DATAURL})
    assert r.status_code == 404


def test_post_render_unknown_fabric_400(client):
    r = client.post(f"/api/garment/{SEED_GARMENT_ID}/render",
                    json={"fabric_id": "no_existe", "flat_png": _DATAURL})
    assert r.status_code == 400


def test_get_renders_lists(client):
    client.post(f"/api/garment/{SEED_GARMENT_ID}/render",
                json={"fabric_id": "denim", "flat_png": _DATAURL})
    body = client.get(f"/api/garment/{SEED_GARMENT_ID}/renders").json()
    assert len(body) == 1
    assert body[0]["fabric_id"] == "denim"
