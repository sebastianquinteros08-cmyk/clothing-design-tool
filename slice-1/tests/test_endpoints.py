import io
from pathlib import Path

from app import pipeline
from app.main import app
from fastapi.testclient import TestClient
from PIL import Image

client = TestClient(app)


def _png_bytes(w=10, h=10):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (0, 128, 255)).save(buf, "PNG")
    return buf.getvalue()


def test_upload_requires_fal_key(monkeypatch):
    monkeypatch.delenv("FAL_KEY", raising=False)
    r = client.post("/api/upload", files={"file": ("t.png", _png_bytes(), "image/png")})
    assert r.status_code == 503


def test_upload_ok(monkeypatch):
    monkeypatch.setenv("FAL_KEY", "test")
    monkeypatch.setattr(pipeline, "upload_image", lambda p: "http://fal/img")
    r = client.post("/api/upload", files={"file": ("t.png", _png_bytes(12, 8), "image/png")})
    assert r.status_code == 200
    data = r.json()
    assert data["width"] == 12 and data["height"] == 8
    assert data["fal_image_url"] == "http://fal/img"
    assert len(data["id"]) == 32
    assert data["image_url"] == f"/work/{data['id']}/original.png"


def test_upload_rejects_non_image(monkeypatch):
    monkeypatch.setenv("FAL_KEY", "test")
    r = client.post("/api/upload", files={"file": ("t.png", b"not an image", "image/png")})
    assert r.status_code == 400


def test_upload_rejects_truncated_image(monkeypatch):
    # PNG con header válido pero datos truncados: Image.open pasa, convert() falla
    # con OSError. Debe devolver 400 (spec §5), no un 500 sin handler.
    monkeypatch.setenv("FAL_KEY", "test")
    buf = io.BytesIO()
    Image.new("RGB", (200, 200), (120, 80, 200)).save(buf, "PNG")
    truncated = buf.getvalue()[:90]
    r = client.post("/api/upload", files={"file": ("t.png", truncated, "image/png")})
    assert r.status_code == 400


def test_segment_bad_id():
    r = client.post("/api/segment", json={"id": "../etc", "fal_image_url": "x", "points": []})
    assert r.status_code == 400


def test_segment_ok(monkeypatch):
    monkeypatch.setenv("FAL_KEY", "test")
    monkeypatch.setattr(pipeline, "upload_image", lambda p: "http://fal/img")
    up = client.post(
        "/api/upload", files={"file": ("t.png", _png_bytes(20, 20), "image/png")}
    ).json()

    monkeypatch.setattr(pipeline, "segment", lambda u, p, b: {"image": {"url": "http://fal/m.png"}})
    monkeypatch.setattr(
        pipeline, "download_mask", lambda url, dest: Path(dest).write_bytes(b"PNGDATA")
    )

    r = client.post("/api/segment", json={
        "id": up["id"], "fal_image_url": up["fal_image_url"],
        "points": [{"x": 5, "y": 5, "label": 1}],
    })
    assert r.status_code == 200
    assert r.json()["mask_url"] == f"/work/{up['id']}/mask.png"


def test_segment_out_of_bounds_point_is_400(monkeypatch):
    monkeypatch.setenv("FAL_KEY", "test")
    monkeypatch.setattr(pipeline, "upload_image", lambda p: "http://fal/img")
    up = client.post(
        "/api/upload", files={"file": ("t.png", _png_bytes(20, 20), "image/png")}
    ).json()
    r = client.post("/api/segment", json={
        "id": up["id"], "fal_image_url": up["fal_image_url"],
        "points": [{"x": 999, "y": 5, "label": 1}],
    })
    assert r.status_code == 400


def test_vectorize_without_mask_is_400(monkeypatch):
    monkeypatch.setenv("FAL_KEY", "test")
    monkeypatch.setattr(pipeline, "upload_image", lambda p: "http://fal/img")
    up = client.post(
        "/api/upload", files={"file": ("t.png", _png_bytes(20, 20), "image/png")}
    ).json()
    r = client.post("/api/vectorize", json={"id": up["id"]})
    assert r.status_code == 400


def test_vectorize_ok(monkeypatch):
    monkeypatch.setenv("FAL_KEY", "test")
    monkeypatch.setattr(pipeline, "upload_image", lambda p: "http://fal/img")
    up = client.post(
        "/api/upload", files={"file": ("t.png", _png_bytes(20, 20), "image/png")}
    ).json()
    # crear máscara fake en el work dir
    from app.main import WORK
    (WORK / up["id"] / "mask.png").write_bytes(_png_bytes(20, 20))

    monkeypatch.setattr(pipeline, "crop_with_mask", lambda o, m, dst: Path(dst).write_bytes(b"X"))
    monkeypatch.setattr(pipeline, "vectorize", lambda i, o: Path(o).write_text("<svg/>"))

    r = client.post("/api/vectorize", json={"id": up["id"]})
    assert r.status_code == 200
    assert r.json()["svg_url"] == f"/work/{up['id']}/flat.svg"


def test_vectorize_pipeline_error_is_500(monkeypatch):
    monkeypatch.setenv("FAL_KEY", "test")
    monkeypatch.setattr(pipeline, "upload_image", lambda p: "http://fal/img")
    up = client.post(
        "/api/upload", files={"file": ("t.png", _png_bytes(20, 20), "image/png")}
    ).json()
    # crear máscara fake en el work dir
    from app.main import WORK
    (WORK / up["id"] / "mask.png").write_bytes(_png_bytes(20, 20))

    monkeypatch.setattr(pipeline, "crop_with_mask", lambda o, m, dst: None)

    def raise_error(*args):
        raise pipeline.PipelineError("vtracer falló")

    monkeypatch.setattr(pipeline, "vectorize", raise_error)

    r = client.post("/api/vectorize", json={"id": up["id"]})
    assert r.status_code == 500
