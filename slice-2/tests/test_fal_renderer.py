import editor.render.backend as backend
from editor.render.backend import FalRenderer


def test_fal_renderer_uploads_subscribes_downloads(monkeypatch, tmp_path):
    swatch = tmp_path / "swatch.png"
    swatch.write_bytes(b"\x89PNG\r\n\x1a\nswatch")
    calls = {}

    def fake_upload(path):
        calls.setdefault("uploads", []).append(path)
        return f"https://fal.cdn/{len(calls['uploads'])}.png"

    def fake_subscribe(model_id, arguments):
        calls["model_id"] = model_id
        calls["arguments"] = arguments
        return {"images": [{"url": "https://fal.cdn/out.png"}]}

    class _Resp:
        content = b"\x89PNG\r\n\x1a\nRESULT"

        def raise_for_status(self): ...

    monkeypatch.setattr(backend.fal_client, "upload_file", fake_upload)
    monkeypatch.setattr(backend.fal_client, "subscribe", fake_subscribe)
    monkeypatch.setattr(backend.requests, "get", lambda url, timeout=0: _Resp())

    out = FalRenderer(model_id="fal-ai/test/edit").render(b"flatpng", str(swatch), "PROMPT")

    assert out == b"\x89PNG\r\n\x1a\nRESULT"
    assert len(calls["uploads"]) == 2  # flat + swatch
    assert calls["model_id"] == "fal-ai/test/edit"
    assert calls["arguments"]["prompt"] == "PROMPT"
    assert len(calls["arguments"]["image_urls"]) == 2
