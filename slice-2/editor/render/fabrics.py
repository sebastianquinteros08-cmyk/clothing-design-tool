"""Biblioteca de telas para el render: presets con swatch + color default.

El render lee de acá, NO del BOM (BOM diferido a Slice 4). swatch_path es
relativo al dir de assets del editor (slice-2/assets/); swatch_url es la ruta
servida por el mount /assets.
"""

from __future__ import annotations

from pydantic import BaseModel


class Fabric(BaseModel):
    id: str
    name: str
    composition: str
    gsm: int | None = None
    swatch_path: str  # relativo a slice-2/assets/, ej "fabrics/lana_melton/swatch.png"
    default_color: str

    @property
    def swatch_url(self) -> str:
        return f"/assets/{self.swatch_path}"


_PRESETS: list[Fabric] = [
    Fabric(id="lana_melton", name="wool melton", composition="100% wool", gsm=450,
           swatch_path="fabrics/lana_melton/swatch.png", default_color="navy"),
    Fabric(id="gabardina", name="cotton gabardine", composition="100% cotton", gsm=300,
           swatch_path="fabrics/gabardina/swatch.png", default_color="beige"),
    Fabric(id="denim", name="denim", composition="100% cotton denim", gsm=380,
           swatch_path="fabrics/denim/swatch.png", default_color="indigo"),
    Fabric(id="cuero", name="leather", composition="full-grain leather",
           swatch_path="fabrics/cuero/swatch.png", default_color="black"),
    Fabric(id="pano", name="wool flannel", composition="100% wool flannel", gsm=340,
           swatch_path="fabrics/pano/swatch.png", default_color="charcoal grey"),
]

_BY_ID = {f.id: f for f in _PRESETS}


def load_fabrics() -> list[Fabric]:
    return list(_PRESETS)


def get_fabric(fabric_id: str) -> Fabric | None:
    return _BY_ID.get(fabric_id)
