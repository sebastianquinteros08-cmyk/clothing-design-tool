import io

import editor.main as main
from editor.detect.detector import FakeDetector
from fastapi.testclient import TestClient
from PIL import Image

from indumentaria.photo import pipeline


def _png_bytes(w=8, h=8):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (10, 20, 30)).save(buf, format="PNG")
    return buf.getvalue()


def _client(tmp_path, monkeypatch):
    # PhotoService de prueba: detector fake + dir temporal; fal/vtracer mockeados.
    monkeypatch.setenv("FAL_KEY", "test-key")
    monkeypatch.setattr(pipeline, "upload_image", lambda p: "http://fal/img.png")
    monkeypatch.setattr(pipeline, "segment", lambda u, p, b: {"image": {"url": "http://fal/m.png"}})
    monkeypatch.setattr(pipeline, "download_mask",
                        lambda url, dest: Image.new("L", (8, 8), 200).save(dest))
    monkeypatch.setattr(pipeline, "crop_with_mask",
                        lambda o, m, d: Image.new("RGBA", (8, 8), (1, 2, 3, 255)).save(d))
    monkeypatch.setattr(pipeline, "vectorize",
                        lambda i, o: o.write_text("<svg/>"))
    from editor.photo import PhotoService
    main.photo_service = PhotoService(FakeDetector(), sessions_dir=tmp_path / "ps")
    return TestClient(main.app)


def test_photo_flow_upload_segment_vectorize_detect(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    up = c.post("/api/photo/upload", files={"file": ("x.png", _png_bytes(), "image/png")})
    assert up.status_code == 200
    sid = up.json()["id"]
    fal_url = up.json()["fal_image_url"]

    seg = c.post("/api/photo/segment",
                 json={"id": sid, "fal_image_url": fal_url,
                       "points": [{"x": 4, "y": 4, "label": 1}]})
    assert seg.status_code == 200 and seg.json()["mask_url"].endswith("mask.png")

    vec = c.post("/api/photo/vectorize", json={"id": sid})
    assert vec.status_code == 200 and vec.json()["svg_url"].endswith("flat.svg")

    det = c.post("/api/photo/detect", json={"id": sid})
    assert det.status_code == 200
    assert det.json()["collar"]["subtype"] == "notch_lapel"


def test_upload_rejects_bad_image(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    r = c.post("/api/photo/upload", files={"file": ("x.png", b"not-an-image", "image/png")})
    assert r.status_code == 400
