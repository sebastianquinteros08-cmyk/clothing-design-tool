# Slice 1 — foto → flat (FastAPI + Konva)

App web local que envuelve el pipeline validado del Slice 0 (SAM 2 + vtracer).
Reemplaza el tipear coordenadas a mano por clickear la prenda en un canvas.

## Correr

```bash
uv run uvicorn app.main:app --app-dir slice-1 --host 127.0.0.1 --port 8000
```

Abrir http://127.0.0.1:8000 (requiere `FAL_KEY` en el `.env` de la raíz del repo).
El server está atado a `127.0.0.1` (no accesible desde la LAN) — uso individual local.

## Flujo

1. **Subir foto** (acepta screenshots sin recortar — SAM 2 ignora la UI de la captura).
2. **Marcar la prenda:** puntos Incluir (+) / Excluir (−) clickeando, o una Caja arrastrando.
   Click sobre un punto existente lo borra.
3. **Segmentar** → ver la máscara superpuesta → corregir puntos → re-segmentar (~$0.003 c/u, contador en pantalla).
4. **Exportar SVG** → preview + descarga de `flat.svg`.

## Arquitectura

- Backend **sin estado** (`app/main.py`): 3 endpoints (`/api/upload`, `/api/segment`, `/api/vectorize`) que envuelven funciones puras de `app/pipeline.py` (refactor del Slice 0). El frontend tiene el estado (id, puntos, caja) y lo reenvía.
- Optimización **upload-once**: la foto se sube a fal.ai una vez; los re-runs reusan la URL.
- Frontend vanilla + Konva vendored (`web/`), sin build step.
- Outputs efímeros por sesión en `work/<id>/` (gitignored).

## Tests

```bash
# Backend (sin gasto — fal.ai mockeado): 25 tests
uv run pytest slice-1/tests/test_pipeline.py slice-1/tests/test_models.py slice-1/tests/test_endpoints.py -v

# Mapeo de coordenadas: verificado en vivo con Playwright MCP (Sesión 5).
# Para correrlo en pytest hace falta instalar el browser (gate §7):
#   uv add --dev pytest-playwright && uv run playwright install chromium
# y la app corriendo. Sin pytest-playwright, el test se auto-skipea.
uv run pytest slice-1/tests/test_coordinate_mapping.py -v
```

## Smoke manual (gasta en fal.ai)

Subir una de las referencias reales validadas en el Slice 0, segmentar con puntos +/−,
exportar, y confirmar que el `flat.svg` es usable. Es la prueba end-to-end del slice.
