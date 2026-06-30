"""Capa de edición: única ruta de escritura sobre el GarmentStore versionado."""

from __future__ import annotations

from editor.models import GarmentSummary
from indumentaria.dsl import versioning
from indumentaria.dsl.garment import Garment
from indumentaria.dsl.operations import CreateGarment, Operation, RestoreVersion
from indumentaria.dsl.store import GarmentStore
from indumentaria.dsl.versioning import GarmentVersion


class GarmentNotFound(Exception):
    """La prenda pedida no existe en el store."""


class EditorService:
    def __init__(self, store: GarmentStore) -> None:
        self._store = store

    def load_head(self, garment_id: str) -> GarmentVersion | None:
        return self._store.get_head(garment_id)

    def get_version(self, garment_id: str, version: int) -> GarmentVersion | None:
        return self._store.get_version(garment_id, version)

    def get_history(self, garment_id: str) -> list[GarmentVersion]:
        return self._store.list_history(garment_id)

    def apply_operation(self, garment_id: str, op: Operation) -> GarmentVersion:
        head = self._store.get_head(garment_id)
        if head is None:
            raise GarmentNotFound(garment_id)
        new_version = versioning.apply(op, head)
        self._store.save_version(new_version, op)
        return new_version

    def restore(
        self, garment_id: str, target_version: int
    ) -> GarmentVersion:
        head = self._store.get_head(garment_id)
        if head is None:
            raise GarmentNotFound(garment_id)
        target = self._store.get_version(garment_id, target_version)
        if target is None:
            raise ValueError(f"versión {target_version} no existe")
        op = RestoreVersion(target_version=target_version, snapshot=target.snapshot)
        new_version = versioning.apply(op, head)
        self._store.save_version(new_version, op)
        return new_version

    def create_garment(self, garment: Garment) -> str:
        op = CreateGarment(garment=garment)
        version = versioning.create_initial(op)
        self._store.save_version(version, op)
        return garment.garment_id

    def list_garments(self) -> list[GarmentSummary]:
        out: list[GarmentSummary] = []
        for gid in self._store.list_garment_ids():
            head = self._store.get_head(gid)
            if head is None:
                continue
            g = head.snapshot
            out.append(GarmentSummary(
                garment_id=gid, name=g.name, garment_type=g.garment_type,
                thumbnail_url=(g.flat.front if g.flat else None),
                version=head.version, updated_at=head.created_at,
            ))
        return out

    def delete_garment(self, garment_id: str) -> None:
        if self._store.get_head(garment_id) is None:
            raise GarmentNotFound(garment_id)
        self._store.delete_garment(garment_id)
