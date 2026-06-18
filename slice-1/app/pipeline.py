"""Núcleo del pipeline foto->flat, refactor del Slice 0 a funciones puras.

Reusa la lógica validada (gate pasado 2026-06-12) pero lanza PipelineError
en vez de sys.exit, para poder envolverlo en endpoints HTTP.
"""

import subprocess
from pathlib import Path

import fal_client
import requests
from PIL import Image


class PipelineError(Exception):
    """Error de dominio del pipeline; el backend lo mapea a un HTTP claro."""


def build_prompts(
    width: int, height: int, points: list[dict], box: dict | None
) -> tuple[list[dict], list[dict]]:
    """Arma point/box prompts para SAM 2 desde coords en píxeles de imagen.

    label 1 = incluir (foreground), 0 = excluir (background).
    Sin ninguna pista, cae al centro de la imagen como único punto positivo.
    """
    prompts: list[dict] = []
    for p in points or []:
        x, y, label = int(p["x"]), int(p["y"]), int(p["label"])
        if not (0 <= x < width and 0 <= y < height):
            raise PipelineError(f"punto ({x},{y}) fuera de la imagen ({width}x{height})")
        if label not in (0, 1):
            raise PipelineError(f"label inválido: {label} (debe ser 0 o 1)")
        prompts.append({"x": x, "y": y, "label": label})

    box_prompts: list[dict] = []
    if box:
        x1, y1 = int(box["x_min"]), int(box["y_min"])
        x2, y2 = int(box["x_max"]), int(box["y_max"])
        box_prompts.append(
            {"x_min": min(x1, x2), "y_min": min(y1, y2),
             "x_max": max(x1, x2), "y_max": max(y1, y2)}
        )

    if not prompts and not box_prompts:
        prompts.append({"x": width // 2, "y": height // 2, "label": 1})

    return prompts, box_prompts


def extract_mask_url(sam_result: dict) -> str:
    """Extrae la URL de la máscara de la respuesta de fal.ai (defensivo)."""
    image = sam_result.get("image")
    if isinstance(image, dict) and image.get("url"):
        return image["url"]
    masks = sam_result.get("masks") or sam_result.get("individual_masks")
    if not masks:
        raise PipelineError(f"SAM 2 no devolvió máscaras: {sam_result}")
    first = masks[0]
    url = (first.get("url") or first.get("image_url")) if isinstance(first, dict) else first
    if not url:
        raise PipelineError(f"no se pudo extraer URL de máscara: {first}")
    return url


def upload_image(path) -> str:
    """Sube la imagen a fal.ai una sola vez y devuelve la URL."""
    return fal_client.upload_file(str(path))


def segment(fal_image_url: str, prompts: list[dict], box_prompts: list[dict]) -> dict:
    """Llama fal-ai/sam2/image. Forma de argumentos validada en Slice 0."""
    arguments: dict = {"image_url": fal_image_url}
    if prompts:
        arguments["prompts"] = prompts
    if box_prompts:
        arguments["box_prompts"] = box_prompts
    return fal_client.subscribe("fal-ai/sam2/image", arguments=arguments, with_logs=False)


def download_mask(mask_url: str, dest) -> None:
    resp = requests.get(mask_url, timeout=30)
    resp.raise_for_status()
    Path(dest).write_bytes(resp.content)


def crop_with_mask(original_path, mask_path, dest) -> None:
    """Aplica la máscara como alpha sobre la imagen original."""
    img = Image.open(original_path).convert("RGBA")
    mask = Image.open(mask_path).convert("L")
    if mask.size != img.size:
        mask = mask.resize(img.size, Image.NEAREST)
    img.putalpha(mask)
    img.save(dest)


def vectorize(input_path, output_path) -> None:
    """Llama vtracer (binario externo) con los flags validados en Slice 0."""
    try:
        subprocess.run(
            ["vtracer", "--input", str(input_path), "--output", str(output_path),
             "--mode", "polygon", "--filter_speckle", "4", "--color_precision", "6"],
            check=True, capture_output=True, text=True,
        )
    except FileNotFoundError as err:
        raise PipelineError("vtracer no está en el PATH") from err
    except subprocess.CalledProcessError as e:
        raise PipelineError(f"vtracer falló: {e.stderr or e.stdout}") from e
