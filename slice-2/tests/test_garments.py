import io

import editor.main as main
from editor.detect.detector import FakeDetector
from editor.photo import PhotoService
from fastapi.testclient import TestClient
from PIL import Image

from indumentaria.photo import pipeline


def _png(w=8, h=8):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (10, 20, 30)).save(buf, format="PNG")
    return buf.getvalue()


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("FAL_KEY", "test-key")
    monkeypatch.setattr(pipeline, "upload_image", lambda p: "http://fal/img.png")
    monkeypatch.setattr(pipeline, "segment", lambda u, p, b: {"image": {"url": "http://fal/m.png"}})
    monkeypatch.setattr(pipeline, "download_mask",
                        lambda url, dest: Image.new("L", (8, 8), 200).save(dest))
    monkeypatch.setattr(pipeline, "crop_with_mask",
                        lambda o, m, d: Image.new("RGBA", (8, 8), (1, 2, 3, 255)).save(d))
    monkeypatch.setattr(pipeline, "vectorize", lambda i, o: open(o, "w").write("<svg/>"))
    # Stores en :memory:, photo en dir temporal, assets en dir temporal.
    main.service = main.EditorService(main.GarmentStore(":memory:"))
    main.photo_service = PhotoService(FakeDetector(), sessions_dir=tmp_path / "ps")
    main.GARMENT_ASSETS = tmp_path / "garments"
    main.GARMENT_ASSETS.mkdir(parents=True, exist_ok=True)
    main.RENDERS = tmp_path / "renders"
    return TestClient(main.app)


def _make_session(c):
    sid = c.post("/api/photo/upload",
                 files={"file": ("x.png", _png(), "image/png")}).json()["id"]
    fal = "http://fal/img.png"
    c.post("/api/photo/segment", json={"id": sid, "fal_image_url": fal,
                                       "points": [{"x": 4, "y": 4, "label": 1}]})
    c.post("/api/photo/vectorize", json={"id": sid})
    return sid


def test_create_from_photo_and_list(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    sid = _make_session(c)
    detected = {"name": "Mi saco", "silhouette": "oversized_cropped",
                "collar": {"subtype": "notch_lapel"},
                "closure": {"subtype": "double_breasted", "button_count": 4, "button_rows": 2},
                "sleeve": {"subtype": "set_in"}, "hem": {"subtype": "straight"}}
    r = c.post("/api/garments", json={"photo_session_id": sid, "detected": detected})
    assert r.status_code == 200
    gid = r.json()["gid"]

    # Los assets se copiaron a data/garments/<gid>/
    assert (main.GARMENT_ASSETS / gid / "flat.svg").exists()
    assert (main.GARMENT_ASSETS / gid / "reference.png").exists()

    # Aparece en la lista con el flat como thumbnail
    lst = c.get("/api/garments").json()
    ids = {g["garment_id"] for g in lst}
    assert gid in ids
    mine = next(g for g in lst if g["garment_id"] == gid)
    assert mine["name"] == "Mi saco"
    assert mine["thumbnail_url"] == f"/garment-assets/{gid}/flat.svg"

    # La prenda es editable/renderizable (tiene flat + componentes)
    g = c.get(f"/api/garment/{gid}").json()["garment"]
    assert g["flat"]["front"] == f"/garment-assets/{gid}/flat.svg"
    assert {comp["kind"] for comp in g["components"]} == {"collar", "closure", "sleeve", "hem"}


def test_delete_garment(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    sid = _make_session(c)
    detected = {"name": "Borrame", "silhouette": "regular", "collar": {"subtype": "band"}}
    gid = c.post("/api/garments",
                 json={"photo_session_id": sid, "detected": detected}).json()["gid"]
    assert c.delete(f"/api/garments/{gid}").status_code == 200
    assert gid not in {g["garment_id"] for g in c.get("/api/garments").json()}
    assert not (main.GARMENT_ASSETS / gid).exists()
    assert not (main.RENDERS / gid).exists()


def test_create_missing_vectorize_400(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    sid = c.post("/api/photo/upload", files={"file": ("x.png", _png(), "image/png")}).json()["id"]
    c.post("/api/photo/segment", json={"id": sid, "fal_image_url": "http://fal/img.png",
                                       "points": [{"x": 4, "y": 4, "label": 1}]})
    # NO vectorize -> la sesión no tiene flat.svg/cropped.png
    detected = {"name": "X", "silhouette": "regular", "collar": {"subtype": "band"}}
    r = c.post("/api/garments", json={"photo_session_id": sid, "detected": detected})
    assert r.status_code == 400


def test_delete_missing_garment_404(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    assert c.delete("/api/garments/nope").status_code == 404
