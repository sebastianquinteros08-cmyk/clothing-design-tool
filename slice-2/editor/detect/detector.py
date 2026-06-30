"""Detección de componentes por IA: pluggable y hermética.

ClaudeDetector usa el SDK oficial anthropic (visión + structured output).
El import de anthropic es lazy para que el módulo cargue aunque la dep no
esté (tests inyectan un cliente fake). FakeDetector cubre los tests."""

from __future__ import annotations

import base64
from typing import Any, Protocol

from editor.detect.schema import (
    DetectedClosure,
    DetectedCollar,
    DetectedGarment,
    DetectedHem,
    DetectedPocket,
    DetectedSleeve,
)

DEFAULT_DETECT_MODEL = "claude-opus-4-8"

_SYSTEM = (
    "You are a fashion technical assistant. You receive a cropped, background-removed "
    "photo of a single garment (a coat/jacket, product flat-lay style). Identify its "
    "structural components and return them in the required structured format: the collar "
    "(and lapel width in cm if it is a lapel), the front closure (subtype, total button "
    "count, number of button rows/columns), the sleeves, the pockets (if any), and the "
    "hem. Also give a short descriptive name and the overall silhouette (e.g. "
    "'oversized_cropped', 'regular', 'longline'). Count buttons carefully. If a component "
    "is not present (e.g. no visible pockets), omit it."
)

_DEFAULT_FAKE = DetectedGarment(
    name="Saco detectado", silhouette="oversized_cropped",
    collar=DetectedCollar(subtype="notch_lapel", lapel_width_cm=8.0),
    closure=DetectedClosure(subtype="double_breasted", button_count=4, button_rows=2),
    sleeve=DetectedSleeve(subtype="set_in", fit="wide_dropped", length="long"),
    pockets=DetectedPocket(subtype="welt", placement="hip", count=2),
    hem=DetectedHem(subtype="straight"),
)


class Detector(Protocol):
    def detect(self, image_bytes: bytes, media_type: str = "image/png") -> DetectedGarment: ...


class FakeDetector:
    def __init__(self, result: DetectedGarment | None = None) -> None:
        self._result = result or _DEFAULT_FAKE

    def detect(self, image_bytes: bytes, media_type: str = "image/png") -> DetectedGarment:
        return self._result


class ClaudeDetector:
    def __init__(self, model: str = DEFAULT_DETECT_MODEL, client: object | None = None) -> None:
        self._model = model
        self._client = client

    def _get_client(self) -> Any:
        if self._client is None:
            import anthropic  # lazy: solo se necesita en producción
            self._client = anthropic.Anthropic()
        return self._client

    def detect(self, image_bytes: bytes, media_type: str = "image/png") -> DetectedGarment:
        b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        resp = self._get_client().messages.parse(
            model=self._model,
            max_tokens=1024,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image",
                     "source": {"type": "base64", "media_type": media_type, "data": b64}},
                    {"type": "text", "text": "Detect the garment's components."},
                ],
            }],
            output_format=DetectedGarment,
        )
        return resp.parsed_output
