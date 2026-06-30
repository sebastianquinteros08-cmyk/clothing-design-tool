from __future__ import annotations

import os
import shutil
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from editor.detect.detector import ClaudeDetector
from editor.detect.schema import to_coat
from editor.models import (
    CreateGarmentRequest,
    DetectRequest,
    OpRequest,
    PhotoSegmentRequest,
    PhotoUploadResponse,
    PhotoVectorizeRequest,
    RenderRequest,
    RestoreRequest,
)
from editor.photo import PhotoError, PhotoService
from editor.render.backend import FalRenderer
from editor.render.fabrics import load_fabrics
from editor.render.service import RenderService
from editor.render.store import RenderStore
from editor.seed import seed
from editor.service import EditorService, GarmentNotFound
from indumentaria.dsl import vocab
from indumentaria.dsl.store import GarmentStore
from indumentaria.dsl.versioning import GarmentVersion
from indumentaria.photo import pipeline

BASE = Path(__file__).resolve().parent.parent  # slice-2/
WEB = BASE / "web"
ASSETS = BASE / "assets"

# Crear dirs antes del mount: StaticFiles lanza RuntimeError si no existen.
ASSETS.mkdir(parents=True, exist_ok=True)
WEB.mkdir(parents=True, exist_ok=True)

# Self-heal del flat: flat.svg es local/gitignored (puede tener una silueta traceada
# de un tercero, no se distribuye). Si falta (clon nuevo), caer al placeholder committeado.
_flat = ASSETS / "peacoat" / "flat.svg"
_flat_placeholder = ASSETS / "peacoat" / "flat.placeholder.svg"
if not _flat.exists() and _flat_placeholder.exists():
    shutil.copy(_flat_placeholder, _flat)

# Store persistente (data/ gitignored, en la raíz del repo). En tests se reemplaza por uno :memory:.
service = EditorService(GarmentStore("data/indumentaria.db"))

DATA = Path("data")
RENDERS = DATA / "renders"
RENDERS.mkdir(parents=True, exist_ok=True)
# Backend de render: FalRenderer real (modelo del spike). En tests se inyecta FakeRenderer.
render_store = RenderStore("data/indumentaria.db")
render_service = RenderService(
    service._store, render_store, FalRenderer(),  # noqa: SLF001
    assets_dir=ASSETS, renders_dir=RENDERS,
)

PHOTO_SESSIONS = DATA / "photo-sessions"
photo_service = PhotoService(ClaudeDetector(), sessions_dir=PHOTO_SESSIONS)

GARMENT_ASSETS = DATA / "garments"
GARMENT_ASSETS.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Siembra el peacoat si la DB está vacía (idempotente). En tests ya se sembró a mano.
    seed(service._store)  # noqa: SLF001
    yield


app = FastAPI(title="diseno-indumentaria Slice 2b", lifespan=lifespan)


@app.middleware("http")
async def _no_cache_static(request, call_next):
    # Dev local single-user: sin caché en estáticos (JS/SVG/renders) para que un
    # asset reemplazado (flat, swatch, render) se vea sin hard-reload del browser.
    response = await call_next(request)
    if not request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


def _payload(version: GarmentVersion) -> dict:
    return {"garment": version.snapshot.model_dump(), "version": version.version}


@app.get("/api/vocab")
def get_vocab() -> dict[str, list[str]]:
    return {
        "collar": sorted(vocab.COLLAR_SUBTYPES),
        "closure": sorted(vocab.CLOSURE_SUBTYPES),
        "sleeve": sorted(vocab.SLEEVE_SUBTYPES),
        "sleeve_fits": sorted(vocab.SLEEVE_FITS),
        "pocket": sorted(vocab.POCKET_SUBTYPES),
        "pocket_placements": sorted(vocab.POCKET_PLACEMENTS),
        "hem": sorted(vocab.HEM_SUBTYPES),
    }


@app.get("/api/garment/{gid}")
def get_garment(gid: str) -> dict:
    head = service.load_head(gid)
    if head is None:
        raise HTTPException(status_code=404, detail="prenda no encontrada")
    return _payload(head)


@app.get("/api/garment/{gid}/version/{n}")
def get_garment_version(gid: str, n: int) -> dict:
    v = service.get_version(gid, n)
    if v is None:
        raise HTTPException(status_code=404, detail="versión no encontrada")
    return _payload(v)


@app.get("/api/garment/{gid}/history")
def get_history(gid: str) -> list[dict]:
    versions = service.get_history(gid)
    return [
        {"version": v.version, "op_type": v.op_type, "created_at": v.created_at.isoformat()}
        for v in versions
    ]


@app.post("/api/garment/{gid}/op")
def apply_op(gid: str, req: OpRequest) -> dict:
    try:
        return _payload(service.apply_operation(gid, req.op))
    except GarmentNotFound as e:
        raise HTTPException(status_code=404, detail="prenda no encontrada") from e
    except (ValueError, ValidationError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/garment/{gid}/restore")
def restore(gid: str, req: RestoreRequest) -> dict:
    try:
        return _payload(service.restore(gid, req.target_version))
    except GarmentNotFound as e:
        raise HTTPException(status_code=404, detail="prenda no encontrada") from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/fabrics")
def get_fabrics() -> list[dict]:
    return [{**f.model_dump(), "swatch_url": f.swatch_url} for f in load_fabrics()]


@app.post("/api/garment/{gid}/render")
def post_render(gid: str, req: RenderRequest) -> dict:
    try:
        rec = render_service.create_render(gid, req.fabric_id, req.color, req.flat_png)
        return rec.model_dump(mode="json")
    except GarmentNotFound as e:
        raise HTTPException(status_code=404, detail="prenda no encontrada") from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/garment/{gid}/renders")
def get_renders(gid: str) -> list[dict]:
    return [r.model_dump(mode="json") for r in render_service.list_renders(gid)]


@app.post("/api/photo/upload", response_model=PhotoUploadResponse)
async def photo_upload(file: UploadFile = File(...)) -> PhotoUploadResponse:  # noqa: B008
    if not os.getenv("FAL_KEY"):
        raise HTTPException(status_code=503, detail="FAL_KEY no configurada en .env")
    raw = await file.read()
    try:
        data = photo_service.upload(raw)
    except PhotoError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"fal.ai no respondió: {e}") from e
    return PhotoUploadResponse(**data)


@app.post("/api/photo/segment")
def photo_segment(req: PhotoSegmentRequest) -> dict:
    try:
        points = [p.model_dump() for p in req.points]
        box = req.box.model_dump() if req.box else None
        return {"mask_url": photo_service.segment(req.id, req.fal_image_url, points, box)}
    except PhotoError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except pipeline.PipelineError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"SAM 2 falló: {e}") from e


@app.post("/api/photo/vectorize")
def photo_vectorize(req: PhotoVectorizeRequest) -> dict:
    try:
        return {"svg_url": photo_service.vectorize(req.id)}
    except PhotoError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except pipeline.PipelineError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/photo/detect")
def photo_detect(req: DetectRequest) -> dict:
    try:
        return photo_service.detect(req.id).model_dump(mode="json")
    except PhotoError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"detector falló: {e}") from e


@app.get("/api/garments")
def list_garments() -> list[dict]:
    out = []
    for s in service.list_garments():
        d = s.model_dump(mode="json")
        renders = render_service.list_renders(s.garment_id)
        if renders:
            d["thumbnail_url"] = renders[0].image_path  # último render manda como thumb
        out.append(d)
    return out


@app.post("/api/garments")
def create_garment(req: CreateGarmentRequest) -> dict:
    try:
        sess = photo_service.session_dir(req.photo_session_id)
    except PhotoError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    flat_src = sess / "flat.svg"
    crop_src = sess / "cropped.png"
    if not flat_src.exists() or not crop_src.exists():
        raise HTTPException(status_code=400, detail="la sesión no tiene flat/recorte")
    gid = uuid4().hex
    dest = GARMENT_ASSETS / gid
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy(flat_src, dest / "flat.svg")
    shutil.copy(crop_src, dest / "reference.png")
    try:
        coat = to_coat(req.detected, gid,
                       flat_front=f"/garment-assets/{gid}/flat.svg",
                       reference_image=f"/garment-assets/{gid}/reference.png")
        service.create_garment(coat)
    except (ValueError, ValidationError) as e:
        shutil.rmtree(dest, ignore_errors=True)
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"gid": gid}


@app.delete("/api/garments/{gid}")
def delete_garment(gid: str) -> dict:
    try:
        service.delete_garment(gid)
    except GarmentNotFound as e:
        raise HTTPException(status_code=404, detail="prenda no encontrada") from e
    render_store.delete_for_garment(gid)
    shutil.rmtree(GARMENT_ASSETS / gid, ignore_errors=True)
    shutil.rmtree(RENDERS / gid, ignore_errors=True)
    return {"ok": True}


# Mounts al final: las rutas /api/* tienen precedencia.
app.mount("/assets", StaticFiles(directory=ASSETS), name="assets")
app.mount("/renders", StaticFiles(directory=RENDERS), name="renders")
PHOTO_SESSIONS.mkdir(parents=True, exist_ok=True)
app.mount("/photo-sessions", StaticFiles(directory=PHOTO_SESSIONS), name="photo-sessions")
app.mount("/garment-assets", StaticFiles(directory=GARMENT_ASSETS), name="garment-assets")
app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
