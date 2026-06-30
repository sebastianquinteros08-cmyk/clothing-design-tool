"""Versioning: cada Operation aplicada produce una GarmentVersion inmutable.

Snapshot para leer/undo/diff rápido; el log de operaciones (store, Task 9) es el
gancho de edición y trazabilidad. La versión linkea la op por op_id+op_type.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from indumentaria.dsl.garment import Garment
from indumentaria.dsl.operations import CreateGarment, Operation


def _now() -> datetime:
    return datetime.now(UTC)


class GarmentVersion(BaseModel):
    model_config = ConfigDict(frozen=True)
    garment_id: str
    version: int
    snapshot: Garment
    op_id: str
    op_type: str
    created_at: datetime


def create_initial(op: CreateGarment, op_id: str | None = None) -> GarmentVersion:
    garment = op.apply()
    return GarmentVersion(
        garment_id=garment.garment_id,
        version=1,
        snapshot=garment,
        op_id=op_id or uuid4().hex,
        op_type=op.op_type,
        created_at=_now(),
    )


def apply(op: Operation, current: GarmentVersion, op_id: str | None = None) -> GarmentVersion:
    new_garment = op.apply(current.snapshot)
    return GarmentVersion(
        garment_id=current.garment_id,
        version=current.version + 1,
        snapshot=new_garment,
        op_id=op_id or uuid4().hex,
        op_type=op.op_type,
        created_at=_now(),
    )
