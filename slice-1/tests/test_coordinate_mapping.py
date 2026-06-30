"""Verifica que el click->coord-de-imagen sea correcto (Global Constraint).

Este es el punto técnico crítico del Slice 1: Konva muestra la foto escalada,
pero SAM 2 necesita coords en píxeles de la imagen original.

Esto se verificó en vivo con automatización de browser:
imagen 1600x1200 -> scale 0.5 -> click en el centro del canvas (display 400,~300)
mapeó a imagen (800, 598) ≈ (800, 600). Correcto.

Este archivo deja el test repetible en pytest. Auto-skip si no está
`pytest-playwright` instalado (instalar: `uv add --dev pytest-playwright` +
`uv run playwright install chromium` — descarga un browser).
Requiere además la app corriendo en 127.0.0.1:8000.

Imagen de prueba: 1600x1200 -> con MAX_W=800, scale=0.5.
Un click en el píxel (200,150) del canvas debe mapear a (400,300) en imagen.
"""

import pytest

playwright = pytest.importorskip("playwright.sync_api")
from PIL import Image  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE_URL = "http://127.0.0.1:8000"


def test_click_maps_to_image_coords(tmp_path):
    big = tmp_path / "big.png"
    Image.new("RGB", (1600, 1200), (200, 200, 200)).save(big)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(BASE_URL)

        # interceptar /api/segment para leer el body y NO gastar en fal.ai
        captured = {}

        def handle(route):
            captured["body"] = route.request.post_data_json
            route.fulfill(
                status=200,
                content_type="application/json",
                body='{"mask_url": "/work/x/mask.png"}',
            )

        page.route("**/api/segment", handle)
        page.set_input_files("#file", str(big))
        page.wait_for_selector("#tools:not([hidden])")
        page.wait_for_timeout(300)  # carga de imagen en canvas

        # click en (200,150) del canvas (origen del canvas)
        box = page.locator("#canvas").bounding_box()
        page.mouse.click(box["x"] + 200, box["y"] + 150)
        page.click("#segment")
        page.wait_for_function("() => true")

        pts = captured["body"]["points"]
        assert pts[0]["x"] == 400 and pts[0]["y"] == 300, pts
        browser.close()
