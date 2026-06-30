# Clothing Design Tool

Turn a **photo of a garment** into a clean, editable design — then restyle it,
render it in new fabrics, and build a personal library of pieces. A local-first
tool for redesigning clothing from visual references without drawing from scratch.

Built as an iterative, slice-based project: it started as a photo → vector-flat
pipeline and grew into a component-based garment editor with AI-assisted
detection and rendering.

## What it does

- **Photo → flat sketch.** Upload a photo, mark the garment on a canvas
  (include/exclude points or a box), segment it with **SAM 2**, and vectorize to
  a clean **SVG flat**.
- **Structured garment model (DSL).** A typed domain model — components,
  materials, measurements, assets and construction vocabulary — so a garment is
  *data*, not just a picture. Edits are precise and fully versioned.
- **Component editor.** Edit collar, closure, sleeves, pockets, hem, fabrics and
  measurements through a web UI; every change is a versioned operation with
  history.
- **AI component detection.** Point the tool at a photo and it proposes a
  structured garment — collar type, button count and rows, pocket placement,
  etc. — using **Claude vision with structured output**. You confirm or correct
  before the garment is created.
- **Generative render.** Visualize a garment in different fabrics and colors with
  an image model (fal.ai), driven by the structured DSL.
- **Multi-garment library.** Create, list and manage multiple garments; each
  keeps its own assets and version history.

## Architecture

Two runnable apps share a common core.

**Core — `src/indumentaria/`**
- `dsl/` — the typed garment model: `garment`, `components`, `materials`,
  `measurements`, `assets`, `vocab`, plus versioned `operations`, a `store`, and
  `versioning`.
- `photo/` — the photo pipeline (SAM 2 segmentation + vtracer vectorization),
  shared by both apps.

**Slice 1 — `slice-1/` (photo → flat)**
A stateless FastAPI backend (`/api/upload`, `/api/segment`, `/api/vectorize`)
wrapping pure pipeline functions, with a vanilla-JS + Konva canvas frontend. The
client holds the state (image id, points, box) and replays it on each call.

**Slice 2 — `slice-2/` (the editor)**
The full tool: a FastAPI app (`editor/`) over the DSL store, with
- `editor/detect/` — a pluggable `Detector` (a fake for tests + a
  `ClaudeDetector` using vision + structured output) that turns a photo into a
  structured garment.
- `editor/render/` — generative rendering from the DSL (fal.ai backend, fabric
  swatches, prompt builder, render store).
- `web/` — a library home, a *new-from-photo* flow, and the component editor
  (vanilla JS + Konva, no build step).

## Tech stack

Python 3.12 · FastAPI · Konva.js · **fal.ai (SAM 2 + image render)** ·
**Anthropic Claude (vision + structured output)** · vtracer · Pillow · pydantic ·
uv · pytest · ruff

## Setup

```bash
uv sync                     # creates .venv and installs dependencies
cp .env.example .env        # then add your keys (see below)
```

`.env` keys:
- `FAL_KEY` — SAM 2 segmentation and image rendering (https://fal.ai/dashboard/keys)
- `ANTHROPIC_API_KEY` — AI component detection (https://console.anthropic.com)

Install **vtracer** (Rust binary, outside pip): grab it from its
[releases](https://github.com/visioncortex/vtracer/releases) and add it to PATH,
or `cargo install vtracer`.

## Run

**The editor (Slice 2) — the full tool:**

```bash
uv run uvicorn editor.main:app --app-dir slice-2 --host 127.0.0.1 --port 8001
# http://127.0.0.1:8001/         → library
# http://127.0.0.1:8001/new.html → create a garment from a photo
```

**The standalone photo → flat app (Slice 1):**

```bash
uv run uvicorn app.main:app --app-dir slice-1 --host 127.0.0.1 --port 8000
# http://127.0.0.1:8000
```

Both bind to `127.0.0.1` (local use only).

## Tests

```bash
uv run pytest -q          # full suite — external services are mocked, no spend
uv run ruff check src slice-1 slice-2 tests
```

## License

MIT — see [LICENSE](LICENSE).
