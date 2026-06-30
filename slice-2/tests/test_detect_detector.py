from editor.detect import schema
from editor.detect.detector import ClaudeDetector, FakeDetector


def test_fake_detector_returns_default():
    d = FakeDetector().detect(b"fake-bytes")
    assert isinstance(d, schema.DetectedGarment)
    assert d.collar is not None


def test_fake_detector_returns_injected():
    custom = schema.DetectedGarment(name="X", silhouette="slim")
    assert FakeDetector(custom).detect(b"x") is custom


class _FakeParsed:
    def __init__(self, parsed):
        self.parsed_output = parsed


class _FakeMessages:
    def __init__(self, parsed):
        self._parsed = parsed
        self.captured = {}

    def parse(self, **kwargs):
        self.captured = kwargs
        return _FakeParsed(self._parsed)


class _FakeClient:
    def __init__(self, parsed):
        self.messages = _FakeMessages(parsed)


def test_claude_detector_wiring():
    expected = schema.DetectedGarment(
        name="Saco", silhouette="regular",
        collar=schema.DetectedCollar(subtype="notch_lapel")
    )
    client = _FakeClient(expected)
    det = ClaudeDetector(client=client)
    out = det.detect(b"\x89PNG-bytes", media_type="image/png")
    assert out is expected
    # Verifica la forma del request: modelo, structured output, imagen base64.
    assert client.messages.captured["model"] == "claude-opus-4-8"
    assert client.messages.captured["output_format"] is schema.DetectedGarment
    content = client.messages.captured["messages"][0]["content"]
    assert content[0]["type"] == "image"
    assert content[0]["source"]["media_type"] == "image/png"
    import base64
    expected_b64 = base64.standard_b64encode(b"\x89PNG-bytes").decode("utf-8")
    assert content[0]["source"]["data"] == expected_b64
    assert "max_tokens" in client.messages.captured
    assert "system" in client.messages.captured
