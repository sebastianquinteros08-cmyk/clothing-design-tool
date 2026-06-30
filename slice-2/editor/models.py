from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from editor.detect.schema import DetectedGarment
from indumentaria.dsl.operations import AnyOperation


class OpRequest(BaseModel):
    op: AnyOperation


class RestoreRequest(BaseModel):
    target_version: int


class RenderRequest(BaseModel):
    fabric_id: str
    color: str | None = None
    flat_png: str  # dataURL "data:image/png;base64,..." exportado por el front


class GarmentSummary(BaseModel):
    garment_id: str
    name: str
    garment_type: str
    thumbnail_url: str | None = None
    version: int
    updated_at: datetime


class PhotoPoint(BaseModel):
    x: int
    y: int
    label: int


class PhotoBox(BaseModel):
    x_min: int
    y_min: int
    x_max: int
    y_max: int


class PhotoUploadResponse(BaseModel):
    id: str
    fal_image_url: str
    image_url: str
    width: int
    height: int


class PhotoSegmentRequest(BaseModel):
    id: str
    fal_image_url: str
    points: list[PhotoPoint] = []
    box: PhotoBox | None = None


class PhotoSegmentResponse(BaseModel):
    mask_url: str


class PhotoVectorizeRequest(BaseModel):
    id: str


class PhotoVectorizeResponse(BaseModel):
    svg_url: str


class DetectRequest(BaseModel):
    id: str


class CreateGarmentRequest(BaseModel):
    photo_session_id: str
    detected: DetectedGarment
