from pydantic import BaseModel, field_validator


class Point(BaseModel):
    x: int
    y: int
    label: int

    @field_validator("label")
    @classmethod
    def _label_valid(cls, v: int) -> int:
        if v not in (0, 1):
            raise ValueError("label debe ser 0 (excluir) o 1 (incluir)")
        return v


class Box(BaseModel):
    x_min: int
    y_min: int
    x_max: int
    y_max: int


class UploadResponse(BaseModel):
    id: str
    fal_image_url: str
    image_url: str
    width: int
    height: int


class SegmentRequest(BaseModel):
    id: str
    fal_image_url: str
    points: list[Point] = []
    box: Box | None = None


class SegmentResponse(BaseModel):
    mask_url: str


class VectorizeRequest(BaseModel):
    id: str


class VectorizeResponse(BaseModel):
    svg_url: str
