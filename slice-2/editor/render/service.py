"""Orquesta el render: lee la versión head (sin escribir DSL), arma prompt,
llama al backend (bytes), guarda imagen + record. Hermético con FakeRenderer.
"""

from __future__ import annotations

import base64
import binascii
from pathlib import Path

from editor.render.backend import RenderBackend
from editor.render.fabrics import get_fabric
from editor.render.prompt import build_render_prompt
from editor.render.store import RenderRecord, RenderStore
from editor.service import GarmentNotFound
from indumentaria.dsl.store import GarmentStore


def _decode_dataurl(dataurl: str) -> bytes:
    """data:image/png;base64,XXXX -> bytes. Acepta también base64 pelado."""
    if dataurl.startswith("data:"):
        _, _, payload = dataurl.partition(",")
        if not payload:
            raise ValueError("flat_png inválido: dataURL sin payload")
    else:
        payload = dataurl
    try:
        return base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as e:
        raise ValueError("flat_png inválido (no es base64)") from e


class RenderService:
    def __init__(
        self,
        garment_store: GarmentStore,
        render_store: RenderStore,
        backend: RenderBackend,
        assets_dir: Path,
        renders_dir: Path,
    ) -> None:
        self._gstore = garment_store
        self._rstore = render_store
        self._backend = backend
        self._assets = Path(assets_dir)
        self._renders = Path(renders_dir)

    def create_render(
        self, garment_id: str, fabric_id: str, color: str | None, flat_png_dataurl: str
    ) -> RenderRecord:
        head = self._gstore.get_head(garment_id)
        if head is None:
            raise GarmentNotFound(garment_id)
        fabric = get_fabric(fabric_id)
        if fabric is None:
            raise ValueError(f"tela desconocida: {fabric_id}")
        chosen_color = color or fabric.default_color
        prompt = build_render_prompt(head.snapshot, fabric, chosen_color)
        flat_png = _decode_dataurl(flat_png_dataurl)
        swatch_path = self._assets / fabric.swatch_path

        png = self._backend.render(flat_png, str(swatch_path), prompt)

        record = RenderRecord(
            garment_id=garment_id, garment_version=head.version, fabric_id=fabric_id,
            color=chosen_color, prompt=prompt, image_path="", model_id=self._backend.model_id,
        )
        dest = self._renders / garment_id / f"{record.id}.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(png)
        record = record.model_copy(update={"image_path": f"/renders/{garment_id}/{record.id}.png"})

        self._rstore.add(record)
        return record

    def list_renders(self, garment_id: str) -> list[RenderRecord]:
        return self._rstore.list_for_garment(garment_id)
