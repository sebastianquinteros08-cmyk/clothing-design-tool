"""Pipeline de foto del editor: wrap de indumentaria.photo + detección, con
storage de sesión bajo data/photo-sessions/<id>/. Sin estado entre llamadas
(el front reenvía el id). Hermético: detector inyectado, funciones de red
del pipeline monkeypatcheables en tests."""

from __future__ import annotations

import io
import re
import uuid
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from editor.detect.detector import Detector
from editor.detect.schema import DetectedGarment
from indumentaria.photo import pipeline

_ID_RE = re.compile(r"^[0-9a-f]{32}$")


class PhotoError(Exception):
    """Error de dominio del flujo de foto (mapea a 4xx)."""


class PhotoService:
    def __init__(self, detector: Detector, sessions_dir: Path) -> None:
        self._detector = detector
        self._dir = Path(sessions_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def session_dir(self, sid: str) -> Path:
        if not _ID_RE.match(sid):
            raise PhotoError("id inválido")
        d = self._dir / sid
        if not d.exists():
            raise PhotoError("sesión no encontrada")
        return d

    def upload(self, raw: bytes) -> dict:
        try:
            with Image.open(io.BytesIO(raw)) as img:
                rgb = img.convert("RGB")
                width, height = rgb.size
        except (UnidentifiedImageError, OSError) as e:
            raise PhotoError("no es una imagen válida") from e
        sid = uuid.uuid4().hex
        d = self._dir / sid
        d.mkdir(parents=True, exist_ok=True)
        rgb.save(d / "original.png")
        fal_url = pipeline.upload_image(d / "original.png")
        return {"id": sid, "fal_image_url": fal_url,
                "image_url": f"/photo-sessions/{sid}/original.png",
                "width": width, "height": height}

    def segment(self, sid: str, fal_image_url: str, points: list[dict],
                box: dict | None) -> str:
        d = self.session_dir(sid)
        with Image.open(d / "original.png") as img:
            width, height = img.size
        prompts, box_prompts = pipeline.build_prompts(width, height, points, box)
        result = pipeline.segment(fal_image_url, prompts, box_prompts)
        mask_url_remote = pipeline.extract_mask_url(result)
        pipeline.download_mask(mask_url_remote, d / "mask.png")
        return f"/photo-sessions/{sid}/mask.png"

    def vectorize(self, sid: str) -> str:
        d = self.session_dir(sid)
        if not (d / "mask.png").exists():
            raise PhotoError("segmentá antes de vectorizar")
        pipeline.crop_with_mask(d / "original.png", d / "mask.png", d / "cropped.png")
        pipeline.vectorize(d / "cropped.png", d / "flat.svg")
        return f"/photo-sessions/{sid}/flat.svg"

    def detect(self, sid: str) -> DetectedGarment:
        d = self.session_dir(sid)
        crop = d / "cropped.png"
        if not crop.exists():
            raise PhotoError("vectorizá (recortá) antes de detectar")
        return self._detector.detect(crop.read_bytes(), media_type="image/png")
