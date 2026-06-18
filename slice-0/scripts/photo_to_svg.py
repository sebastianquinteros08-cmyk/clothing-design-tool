"""
Slice 0 - photo_to_svg.py

Pipeline foto -> flat SVG via SAM 2 (fal.ai) + vtracer.

Usage:
    uv run slice-0/scripts/photo_to_svg.py <photo_path> [--point X,Y ...] [--neg X,Y ...] [--box X1,Y1,X2,Y2]

    Sin pistas usa el centro como punto positivo. Para aislar una sola prenda de una
    foto con modelo/varias prendas: --point sobre la prenda (repetible) + --neg sobre
    lo que hay que excluir (cabeza, otra prenda, fondo).

Outputs (en slice-0/output/<photo_name>/):
    mask.png             mascara binaria de SAM 2
    cropped.png          prenda recortada con fondo transparente
    flat.svg             vectorizado por vtracer
    meta.json            timing por etapa + costo estimado
    sam2_response.json   respuesta cruda de fal.ai (debug)
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import fal_client
import requests
from dotenv import load_dotenv
from PIL import Image

# Pricing aproximado (fal.ai 2026, actualizar si cambia el modelo o la tarifa).
# SAM 2 image en fal.ai cuesta ~$0.0012/s GPU; cada call promedia ~2s.
FAL_SAM2_COST_PER_CALL = 0.003


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("photo", type=Path, help="Path al archivo de foto (jpg, png).")
    parser.add_argument(
        "--point",
        action="append",
        default=None,
        metavar="X,Y",
        help="Punto positivo 'incluir esto' para SAM 2. Repetible. "
        "Default: centro de la imagen. Ej: --point 400,500 --point 420,800",
    )
    parser.add_argument(
        "--neg",
        action="append",
        default=None,
        metavar="X,Y",
        help="Punto negativo 'excluir esto' (ej: cabeza, otra prenda, fondo). Repetible. "
        "Sirve para aislar una sola prenda cuando SAM 2 agarra de mas. Ej: --neg 640,200",
    )
    parser.add_argument(
        "--box",
        type=str,
        default=None,
        metavar="X1,Y1,X2,Y2",
        help="Bounding box que encierra la prenda (alternativa o complemento a --point). "
        "Ej: --box 100,200,900,1400",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directorio de salida (default: slice-0/output/<photo_stem>/).",
    )
    return parser.parse_args()


def _parse_xy(s: str, w: int, h: int) -> tuple[int, int]:
    """Parsea 'x,y' a enteros y valida que caiga dentro de la imagen."""
    try:
        x, y = map(int, s.split(","))
    except ValueError:
        sys.exit(f"ERROR: punto debe ser 'x,y' con enteros. Recibido: {s}")
    if not (0 <= x < w and 0 <= y < h):
        sys.exit(f"ERROR: punto ({x},{y}) fuera de los limites de la imagen ({w}x{h})")
    return (x, y)


def build_prompts(
    image_path: Path,
    pos_strs: list[str] | None,
    neg_strs: list[str] | None,
    box_str: str | None,
) -> tuple[list[dict], list[dict]]:
    """Arma point prompts + box prompts para SAM 2 desde los args CLI.

    label 1 = foreground (incluir), label 0 = background (excluir).
    Sin ninguna pista, cae al centro de la imagen como unico punto positivo
    (conserva el comportamiento previo del script).
    """
    with Image.open(image_path) as img:
        w, h = img.size

    prompts: list[dict] = []
    for s in pos_strs or []:
        x, y = _parse_xy(s, w, h)
        prompts.append({"x": x, "y": y, "label": 1})
    for s in neg_strs or []:
        x, y = _parse_xy(s, w, h)
        prompts.append({"x": x, "y": y, "label": 0})

    box_prompts: list[dict] = []
    if box_str:
        try:
            x1, y1, x2, y2 = map(int, box_str.split(","))
        except ValueError:
            sys.exit(f"ERROR: --box debe ser 'x1,y1,x2,y2' con enteros. Recibido: {box_str}")
        box_prompts.append(
            {
                "x_min": min(x1, x2),
                "y_min": min(y1, y2),
                "x_max": max(x1, x2),
                "y_max": max(y1, y2),
            }
        )

    if not prompts and not box_prompts:
        prompts.append({"x": w // 2, "y": h // 2, "label": 1})

    return prompts, box_prompts


def segment_with_sam2(image_path: Path, prompts: list[dict], box_prompts: list[dict]) -> dict:
    """Sube la imagen a fal.ai, llama SAM 2 image, devuelve el resultado + timing."""
    print(f"  Subiendo {image_path.name} a fal.ai...")
    upload_start = time.time()
    image_url = fal_client.upload_file(str(image_path))
    upload_time = time.time() - upload_start

    n_pos = sum(1 for p in prompts if p["label"] == 1)
    n_neg = sum(1 for p in prompts if p["label"] == 0)
    print(
        f"  Upload OK ({upload_time:.1f}s). SAM 2: {n_pos} punto(s)+, "
        f"{n_neg} punto(s)-, {len(box_prompts)} box..."
    )
    sam_start = time.time()
    # NOTA: la API de fal.ai espera 'prompts' (point prompts {x,y,label}) y/o
    # 'box_prompts' ({x_min,y_min,x_max,y_max}). Verificado contra la doc del
    # endpoint y el error 422 (2026-06-12).
    arguments: dict = {"image_url": image_url}
    if prompts:
        arguments["prompts"] = prompts
    if box_prompts:
        arguments["box_prompts"] = box_prompts
    result = fal_client.subscribe(
        "fal-ai/sam2/image",
        arguments=arguments,
        with_logs=False,
    )
    sam_time = time.time() - sam_start

    return {
        "result": result,
        "upload_time": upload_time,
        "sam_time": sam_time,
        "image_url": image_url,
    }


def extract_mask_url(sam_result: dict) -> str:
    """Extrae la URL de la mascara desde la respuesta de fal.ai (defensivo)."""
    # Formato actual de fal-ai/sam2/image (2026-06): {'image': {'url': ...}} con la mascara unica.
    image = sam_result.get("image")
    if isinstance(image, dict) and image.get("url"):
        return image["url"]
    masks = sam_result.get("masks") or sam_result.get("individual_masks")
    if not masks:
        raise RuntimeError(f"SAM 2 no devolvio mascaras. Respuesta: {sam_result}")
    first = masks[0]
    if isinstance(first, dict):
        url = first.get("url") or first.get("image_url")
    else:
        url = first
    if not url:
        raise RuntimeError(f"No se pudo extraer URL de la primera mascara: {first}")
    return url


def download_mask(mask_url: str, output_path: Path) -> None:
    print("  Bajando mascara...")
    response = requests.get(mask_url, timeout=30)
    response.raise_for_status()
    output_path.write_bytes(response.content)


def crop_with_mask(image_path: Path, mask_path: Path, output_path: Path) -> None:
    """Aplica la mascara a la imagen original y guarda PNG con alpha."""
    print("  Recortando imagen con mascara...")
    img = Image.open(image_path).convert("RGBA")
    mask = Image.open(mask_path).convert("L")
    if mask.size != img.size:
        mask = mask.resize(img.size, Image.NEAREST)
    img.putalpha(mask)
    img.save(output_path)


def vectorize_with_vtracer(input_path: Path, output_path: Path) -> float:
    """Llama vtracer (binario externo) y devuelve el tiempo de ejecucion."""
    print(f"  Vectorizando con vtracer -> {output_path.name}...")
    start = time.time()
    try:
        subprocess.run(
            [
                "vtracer",
                "--input", str(input_path),
                "--output", str(output_path),
                "--mode", "polygon",
                "--filter_speckle", "4",
                "--color_precision", "6",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        sys.exit(
            "ERROR: vtracer no esta instalado o no esta en el PATH.\n"
            "Instalar binario de https://github.com/visioncortex/vtracer/releases "
            "o con `cargo install vtracer`."
        )
    except subprocess.CalledProcessError as e:
        sys.exit(f"ERROR vtracer: {e.stderr or e.stdout}")
    return time.time() - start


def main() -> int:
    args = parse_args()

    if not args.photo.exists():
        sys.exit(f"ERROR: no existe el archivo {args.photo}")

    load_dotenv()
    if not os.getenv("FAL_KEY"):
        sys.exit("ERROR: FAL_KEY no esta en .env. Copia .env.example a .env y configura la key.")

    output_dir = args.output_dir or Path("slice-0/output") / args.photo.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    prompts, box_prompts = build_prompts(args.photo, args.point, args.neg, args.box)
    print(f"\n-> Procesando {args.photo.name}")
    print(f"  Prompts SAM 2: {prompts}")
    if box_prompts:
        print(f"  Box SAM 2: {box_prompts}")
    print(f"  Output: {output_dir}")

    total_start = time.time()

    sam_data = segment_with_sam2(args.photo, prompts, box_prompts)

    # Guardar respuesta cruda para debug (si SAM 2 cambia formato, util para ajustar)
    (output_dir / "sam2_response.json").write_text(
        json.dumps(sam_data["result"], indent=2, ensure_ascii=False, default=str)
    )

    try:
        mask_url = extract_mask_url(sam_data["result"])
    except RuntimeError as e:
        sys.exit(f"ERROR: {e}\nRespuesta guardada en {output_dir}/sam2_response.json para debug.")

    mask_path = output_dir / "mask.png"
    download_mask(mask_url, mask_path)

    cropped_path = output_dir / "cropped.png"
    crop_with_mask(args.photo, mask_path, cropped_path)

    svg_path = output_dir / "flat.svg"
    vtracer_time = vectorize_with_vtracer(cropped_path, svg_path)

    total_time = time.time() - total_start

    meta = {
        "photo": str(args.photo),
        "prompts_sam2": prompts,
        "box_prompts_sam2": box_prompts,
        "timing_s": {
            "upload": round(sam_data["upload_time"], 2),
            "sam2": round(sam_data["sam_time"], 2),
            "vtracer": round(vtracer_time, 2),
            "total": round(total_time, 2),
        },
        "cost_estimate_usd": {
            "sam2_call": FAL_SAM2_COST_PER_CALL,
            "total_estimated": FAL_SAM2_COST_PER_CALL,
            "note": (
                "Estimacion basada en ~2s GPU @ $0.0012/s para SAM 2 image. "
                "Para costo real, ver dashboard de fal.ai (https://fal.ai/dashboard/usage). "
                "Si el pricing cambia, actualizar FAL_SAM2_COST_PER_CALL en este script."
            ),
        },
        "outputs": {
            "mask": "mask.png",
            "cropped": "cropped.png",
            "svg": "flat.svg",
            "sam2_response": "sam2_response.json",
        },
    }
    (output_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))

    print(f"\nOK Listo en {total_time:.1f}s")
    print(f"  Mask:    {mask_path}")
    print(f"  Cropped: {cropped_path}")
    print(f"  SVG:     {svg_path}")
    print(f"  Meta:    {output_dir / 'meta.json'}")
    print(f"  Costo estimado: ~${FAL_SAM2_COST_PER_CALL:.4f} USD")
    print("\nPara verificar costo real, ver https://fal.ai/dashboard/usage")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
