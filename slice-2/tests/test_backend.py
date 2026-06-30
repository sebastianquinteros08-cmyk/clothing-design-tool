from editor.render.backend import FakeRenderer


def test_fake_renderer_returns_png_bytes():
    out = FakeRenderer().render(b"flat", "swatch.png", "a prompt")
    assert isinstance(out, bytes)
    assert out[:8] == b"\x89PNG\r\n\x1a\n"  # firma PNG


def test_fake_renderer_has_model_id():
    assert FakeRenderer().model_id == "fake"
    assert FakeRenderer(model_id="x").model_id == "x"
