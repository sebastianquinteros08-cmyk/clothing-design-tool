# Clothing Design Tool — photo → flat sketch (SVG)

A local-first tool that turns a **photo of a garment** into a clean, editable
**vector flat sketch** (SVG) — so you can redesign clothing from visual
references without drawing from scratch.

Built as an iterative, slice-based project. Current pipeline: upload a photo →
mark the garment with include/exclude points and a box on a canvas → segment it
with **SAM 2** → vectorize → export SVG.

## Architecture

- **Backend — FastAPI** (`slice-1/app/`): stateless API (`/api/upload`,
  `/api/segment`, `/api/vectorize`) wrapping pure pipeline functions. The client
  holds the state (image id, points, box) and replays it on each call.
- **Frontend — vanilla JS + Konva.js** (`slice-1/web/`): a canvas where you
  click include (+) / exclude (−) points or drag a box. No build step.
- **Segmentation:** SAM 2 via [fal.ai](https://fal.ai) (~$0.003 per run; the
  image is uploaded once and re-runs reuse the URL).
- **Vectorization:** [vtracer](https://github.com/visioncortex/vtracer) (Rust
  binary) → SVG.
- **Garment DSL** (`src/indumentaria/dsl/`): a typed domain model (garment,
  components, materials, measurements, assets) — the basis for a structured,
  component-based editor.

## Tech stack

Python 3.12 · FastAPI · Konva.js · fal.ai (SAM 2) · vtracer · Pillow · pydantic
· uv · pytest · ruff

## Setup

```bash
uv sync                     # creates .venv and installs dependencies
cp .env.example .env        # then paste your FAL_KEY (https://fal.ai/dashboard/keys)
```

Install **vtracer** (Rust binary, outside pip): download from its
[releases](https://github.com/visioncortex/vtracer/releases) and add it to PATH,
or `cargo install vtracer`.

## Run the web app

```bash
uv run uvicorn app.main:app --app-dir slice-1 --host 127.0.0.1 --port 8000
# open http://127.0.0.1:8000
```

## Tests

```bash
uv run pytest          # fal.ai is mocked — no API spend
```

## Project structure

```
slice-0/scripts/   # CLI pipeline: photo -> flat SVG
slice-1/app/       # FastAPI backend (stateless)
slice-1/web/       # Konva.js frontend (no build step)
slice-1/tests/     # pipeline + endpoint tests (fal.ai mocked)
src/indumentaria/  # typed garment DSL
tests/             # DSL tests
```

> Personal input photos, generated outputs and API keys are gitignored and are
> not part of this repository.

## License

MIT © 2026 Sebastian Quinteros Moretto
