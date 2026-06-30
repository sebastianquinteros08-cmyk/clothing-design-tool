import subprocess

import pytest
from PIL import Image

from indumentaria.photo import pipeline


def test_build_prompts_default_center():
    prompts, boxes = pipeline.build_prompts(100, 200, [], None)
    assert prompts == [{"x": 50, "y": 100, "label": 1}]
    assert boxes == []


def test_build_prompts_out_of_bounds_raises():
    with pytest.raises(pipeline.PipelineError):
        pipeline.build_prompts(100, 100, [{"x": 200, "y": 10, "label": 1}], None)


def test_build_prompts_bad_label_raises():
    with pytest.raises(pipeline.PipelineError):
        pipeline.build_prompts(100, 100, [{"x": 10, "y": 10, "label": 5}], None)


def test_build_prompts_box_normalized():
    _, boxes = pipeline.build_prompts(
        100, 100, [], {"x_min": 80, "y_min": 90, "x_max": 10, "y_max": 20}
    )
    assert boxes == [{"x_min": 10, "y_min": 20, "x_max": 80, "y_max": 90}]


def test_build_prompts_keeps_points_and_box():
    prompts, boxes = pipeline.build_prompts(
        100, 100, [{"x": 10, "y": 20, "label": 0}], {"x_min": 0, "y_min": 0, "x_max": 5, "y_max": 5}
    )
    assert prompts == [{"x": 10, "y": 20, "label": 0}]
    assert boxes == [{"x_min": 0, "y_min": 0, "x_max": 5, "y_max": 5}]


def test_extract_mask_url_image_dict():
    assert pipeline.extract_mask_url({"image": {"url": "http://x/m.png"}}) == "http://x/m.png"


def test_extract_mask_url_masks_list():
    assert pipeline.extract_mask_url({"masks": [{"url": "http://x/0.png"}]}) == "http://x/0.png"


def test_extract_mask_url_no_mask_raises():
    with pytest.raises(pipeline.PipelineError):
        pipeline.extract_mask_url({})


def test_segment_passes_validated_args(monkeypatch):
    captured = {}

    def fake_subscribe(model, arguments, with_logs):
        captured["model"] = model
        captured["args"] = arguments
        return {"image": {"url": "http://x/m.png"}}

    monkeypatch.setattr(pipeline.fal_client, "subscribe", fake_subscribe)
    out = pipeline.segment("http://img", [{"x": 1, "y": 2, "label": 1}], [])
    assert captured["model"] == "fal-ai/sam2/image"
    assert captured["args"]["image_url"] == "http://img"
    assert captured["args"]["prompts"] == [{"x": 1, "y": 2, "label": 1}]
    assert "box_prompts" not in captured["args"]
    assert out == {"image": {"url": "http://x/m.png"}}


def test_crop_with_mask_applies_alpha(tmp_path):
    orig = tmp_path / "o.png"
    Image.new("RGB", (4, 4), (255, 0, 0)).save(orig)
    mask = tmp_path / "m.png"
    Image.new("L", (4, 4), 128).save(mask)
    out = tmp_path / "c.png"
    pipeline.crop_with_mask(orig, mask, out)
    res = Image.open(out)
    assert res.mode == "RGBA"
    assert res.getpixel((0, 0))[3] == 128


def test_vectorize_missing_binary_raises(monkeypatch, tmp_path):
    def boom(*a, **k):
        raise FileNotFoundError

    monkeypatch.setattr(pipeline.subprocess, "run", boom)
    with pytest.raises(pipeline.PipelineError):
        pipeline.vectorize(tmp_path / "i.png", tmp_path / "o.svg")


def test_vectorize_nonzero_exit_raises(monkeypatch, tmp_path):
    def boom(*a, **k):
        raise subprocess.CalledProcessError(1, "vtracer", stderr="boom")

    monkeypatch.setattr(pipeline.subprocess, "run", boom)
    with pytest.raises(pipeline.PipelineError):
        pipeline.vectorize(tmp_path / "i.png", tmp_path / "o.svg")
