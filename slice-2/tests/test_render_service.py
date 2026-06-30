import base64

import pytest
from editor.render.backend import FakeRenderer
from editor.render.service import RenderService
from editor.render.store import RenderStore
from editor.seed import SEED_GARMENT_ID, seed
from editor.service import GarmentNotFound

from indumentaria.dsl.store import GarmentStore

_DATAURL = "data:image/png;base64," + base64.b64encode(b"flatpng").decode()


@pytest.fixture
def svc(tmp_path):
    gstore = GarmentStore(":memory:")
    seed(gstore)
    rstore = RenderStore(":memory:")
    service = RenderService(gstore, rstore, FakeRenderer(model_id="fake"),
                            assets_dir=tmp_path / "assets", renders_dir=tmp_path / "renders")
    yield service
    gstore.close()
    rstore.close()


def test_create_render_writes_file_and_record(svc, tmp_path):
    rec = svc.create_render(SEED_GARMENT_ID, "lana_melton", None, _DATAURL)
    assert rec.fabric_id == "lana_melton"
    assert rec.color == "navy"  # default de la tela
    assert rec.garment_version == 1
    assert rec.model_id == "fake"
    assert rec.image_path == f"/renders/{SEED_GARMENT_ID}/{rec.id}.png"
    written = tmp_path / "renders" / SEED_GARMENT_ID / f"{rec.id}.png"
    assert written.exists() and written.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_create_render_explicit_color(svc):
    rec = svc.create_render(SEED_GARMENT_ID, "denim", "black", _DATAURL)
    assert rec.color == "black"


def test_create_render_unknown_garment_raises(svc):
    with pytest.raises(GarmentNotFound):
        svc.create_render("nope", "denim", None, _DATAURL)


def test_create_render_unknown_fabric_raises(svc):
    with pytest.raises(ValueError, match="tela"):
        svc.create_render(SEED_GARMENT_ID, "no_existe", None, _DATAURL)


def test_list_renders_returns_added(svc):
    svc.create_render(SEED_GARMENT_ID, "denim", None, _DATAURL)
    svc.create_render(SEED_GARMENT_ID, "cuero", None, _DATAURL)
    assert len(svc.list_renders(SEED_GARMENT_ID)) == 2


def test_create_render_invalid_flat_raises(svc):
    with pytest.raises(ValueError, match="base64"):
        svc.create_render(SEED_GARMENT_ID, "denim", None, "not-valid-b64!!!")
