import io
import os
import re
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError

from app import pipeline
from app.models import (
    SegmentRequest,
    SegmentResponse,
    UploadResponse,
    VectorizeRequest,
    VectorizeResponse,
)

BASE = Path(__file__).resolve().parent.parent          # slice-1/
WEB = BASE / "web"
WORK = BASE / "work"
WORK.mkdir(exist_ok=True)
load_dotenv(BASE.parent / ".env")                       # .env en la raíz del repo

ID_RE = re.compile(r"^[0-9a-f]{32}$")

app = FastAPI(title="diseno-indumentaria Slice 1")


def _work_dir(id: str) -> Path:
    if not ID_RE.match(id):
        raise HTTPException(status_code=400, detail="id inválido")
    d = WORK / id
    if not d.exists():
        raise HTTPException(status_code=404, detail="sesión no encontrada")
    return d


@app.post("/api/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)) -> UploadResponse:  # noqa: B008
    if not os.getenv("FAL_KEY"):
        raise HTTPException(status_code=503, detail="FAL_KEY no configurada en .env")
    raw = await file.read()
    # Validar la imagen: convert() fuerza la decodificación, así que un archivo con
    # header válido pero datos truncados/corruptos falla acá con OSError (no solo
    # UnidentifiedImageError). Ambos se mapean a 400 (spec §5: "no es una imagen válida").
    try:
        with Image.open(io.BytesIO(raw)) as img:
            rgb = img.convert("RGB")
            width, height = rgb.size
    except (UnidentifiedImageError, OSError) as e:
        raise HTTPException(status_code=400, detail="no es una imagen válida") from e
    sid = uuid.uuid4().hex
    d = WORK / sid
    d.mkdir(parents=True, exist_ok=True)
    rgb.save(d / "original.png")
    try:
        fal_image_url = pipeline.upload_image(d / "original.png")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"fal.ai no respondió: {e}") from e
    return UploadResponse(
        id=sid, fal_image_url=fal_image_url,
        image_url=f"/work/{sid}/original.png", width=width, height=height,
    )


@app.post("/api/segment", response_model=SegmentResponse)
def segment(req: SegmentRequest) -> SegmentResponse:
    d = _work_dir(req.id)
    original = d / "original.png"
    with Image.open(original) as img:
        width, height = img.size

    points = [p.model_dump() for p in req.points]
    box = req.box.model_dump() if req.box else None
    try:
        prompts, box_prompts = pipeline.build_prompts(width, height, points, box)
    except pipeline.PipelineError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        result = pipeline.segment(req.fal_image_url, prompts, box_prompts)
        mask_url_remote = pipeline.extract_mask_url(result)
        pipeline.download_mask(mask_url_remote, d / "mask.png")
    except pipeline.PipelineError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"SAM 2 falló: {e}") from e

    return SegmentResponse(mask_url=f"/work/{req.id}/mask.png")


@app.post("/api/vectorize", response_model=VectorizeResponse)
def vectorize(req: VectorizeRequest) -> VectorizeResponse:
    d = _work_dir(req.id)
    mask = d / "mask.png"
    if not mask.exists():
        raise HTTPException(status_code=400, detail="segmentá antes de vectorizar")
    try:
        pipeline.crop_with_mask(d / "original.png", mask, d / "cropped.png")
        pipeline.vectorize(d / "cropped.png", d / "flat.svg")
    except pipeline.PipelineError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return VectorizeResponse(svg_url=f"/work/{req.id}/flat.svg")


# Mounts AL FINAL: las rutas /api/* ya están registradas y tienen precedencia.
app.mount("/work", StaticFiles(directory=WORK), name="work")
app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
