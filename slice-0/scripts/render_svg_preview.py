"""
Slice 0 - render_svg_preview.py (utilidad de inspeccion)

Rasteriza los SVG que produce vtracer en --mode polygon (paths M/L/Z + translate)
a PNG con Pillow, para poder inspeccionar el flat sin un browser/editor SVG.
NO es un renderer SVG general — solo cubre el subset que emite vtracer polygon.

Usage:
    uv run slice-0/scripts/render_svg_preview.py <flat.svg> [out.png]
"""

import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw


def parse_subpaths(d: str) -> list[list[tuple[float, float]]]:
    """Parsea un atributo d con M/L/Z (solo lineas rectas) en lista de poligonos."""
    polys = []
    for sub in re.split(r"[Zz]", d):
        coords = re.findall(r"(-?\d+\.?\d*),(-?\d+\.?\d*)", sub)
        if len(coords) >= 3:
            polys.append([(float(x), float(y)) for x, y in coords])
    return polys


def main() -> int:
    svg_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else svg_path.with_suffix(".preview.png")
    svg = svg_path.read_text()

    size = re.search(r'width="(\d+)" height="(\d+)"', svg)
    if not size:
        sys.exit("ERROR: no pude leer width/height del SVG")
    w, h = int(size.group(1)), int(size.group(2))

    scale = 2  # supersample para que las lineas se vean nitidas
    img = Image.new("RGB", (w * scale, h * scale), "#FFFFFF")
    draw = ImageDraw.Draw(img)

    paths = re.findall(r'<path d="([^"]+)" fill="([^"]+)"(?: transform="translate\((-?\d+),(-?\d+)\)")?', svg)
    if not paths:
        sys.exit("ERROR: no encontre paths con el formato esperado de vtracer")

    for d, fill, tx, ty in paths:
        dx, dy = float(tx or 0), float(ty or 0)
        for poly in parse_subpaths(d):
            pts = [((x + dx) * scale, (y + dy) * scale) for x, y in poly]
            draw.polygon(pts, fill=fill)

    img = img.resize((w, h), Image.LANCZOS)
    img.save(out_path)
    print(f"OK {len(paths)} paths -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
