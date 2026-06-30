"""RenderBackend: abstrae el motor de render. Toda la RED vive acá adentro.

render() recibe el flat ya rasterizado (PNG bytes) + la ruta del swatch + el
prompt, y devuelve la imagen final como BYTES. Así el RenderService es hermético
(con FakeRenderer no toca la red). FalRenderer (Task 7) hace upload+subscribe+
download de fal.ai puertas adentro.
"""

from __future__ import annotations

import base64
import tempfile
from pathlib import Path
from typing import Protocol

import fal_client
import requests

# 1x1 PNG válido (transparente), para tests/E2E deterministas.
_FAKE_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M8AAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
)


class RenderBackend(Protocol):
    model_id: str

    def render(self, flat_png: bytes, swatch_path: str, prompt: str) -> bytes: ...


class FakeRenderer:
    """Backend determinista para tests/E2E. No toca la red."""

    def __init__(self, model_id: str = "fake") -> None:
        self.model_id = model_id

    def render(self, flat_png: bytes, swatch_path: str, prompt: str) -> bytes:
        return _FAKE_PNG


# Modelo elegido por su fidelidad a la silueta del DSL y su velocidad.
DEFAULT_RENDER_MODEL = "fal-ai/nano-banana-2/edit"


class FalRenderer:
    """Backend real fal.ai. Multi-referencia: [flat, swatch] + prompt del DSL.

    Toda la red vive acá: upload del flat (PNG bytes) + swatch + subscribe + download.
    """

    def __init__(self, model_id: str = DEFAULT_RENDER_MODEL) -> None:
        self.model_id = model_id

    def render(self, flat_png: bytes, swatch_path: str, prompt: str) -> bytes:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
            tf.write(flat_png)
            flat_tmp = tf.name
        try:
            flat_url = fal_client.upload_file(flat_tmp)
            swatch_url = fal_client.upload_file(swatch_path)
        finally:
            Path(flat_tmp).unlink(missing_ok=True)
        result = fal_client.subscribe(
            self.model_id,
            arguments={"prompt": prompt, "image_urls": [flat_url, swatch_url]},
        )
        images = result.get("images") or []
        if not images or not images[0].get("url"):
            raise RuntimeError(f"render fal sin imagen: {result}")
        resp = requests.get(images[0]["url"], timeout=120)
        resp.raise_for_status()
        return resp.content
