import pytest
from app import models
from pydantic import ValidationError


def test_point_accepts_valid_label():
    p = models.Point(x=1, y=2, label=1)
    assert p.label == 1


def test_point_rejects_bad_label():
    with pytest.raises(ValidationError):
        models.Point(x=1, y=2, label=7)


def test_segment_request_defaults():
    r = models.SegmentRequest(id="abc", fal_image_url="http://x")
    assert r.points == []
    assert r.box is None


def test_upload_response_fields():
    r = models.UploadResponse(
        id="abc", fal_image_url="http://x", image_url="/work/abc/original.png",
        width=10, height=20,
    )
    assert r.width == 10 and r.image_url.endswith("original.png")
