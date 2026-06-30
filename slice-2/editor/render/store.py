"""Persistencia de renders: tabla `renders`, FUERA del version chain del DSL.

Los renders son artefactos derivados, no estado de diseño. Borrar un render no
afecta la prenda. Comparte el archivo de DB con el GarmentStore pero en su
propia tabla y conexión.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field

_SCHEMA = """
CREATE TABLE IF NOT EXISTS renders (
  id              TEXT PRIMARY KEY,
  garment_id      TEXT NOT NULL,
  garment_version INTEGER NOT NULL,
  fabric_id       TEXT NOT NULL,
  color           TEXT NOT NULL,
  prompt          TEXT NOT NULL,
  image_path      TEXT NOT NULL,
  model_id        TEXT NOT NULL,
  created_at      TEXT NOT NULL
);
"""


class RenderRecord(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    garment_id: str
    garment_version: int
    fabric_id: str
    color: str
    prompt: str
    image_path: str
    model_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RenderStore:
    def __init__(self, db_path: str | Path = "data/indumentaria.db") -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)

    def add(self, record: RenderRecord) -> None:
        self._conn.execute(
            "INSERT INTO renders (id, garment_id, garment_version, fabric_id, color, "
            "prompt, image_path, model_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (record.id, record.garment_id, record.garment_version, record.fabric_id,
             record.color, record.prompt, record.image_path, record.model_id,
             record.created_at.isoformat()),
        )
        self._conn.commit()

    def list_for_garment(self, garment_id: str) -> list[RenderRecord]:
        rows = self._conn.execute(
            "SELECT id, garment_id, garment_version, fabric_id, color, prompt, "
            "image_path, model_id, created_at FROM renders WHERE garment_id = ? "
            "ORDER BY created_at DESC, rowid DESC",
            (garment_id,),
        ).fetchall()
        return [self._row(r) for r in rows]

    def get(self, render_id: str) -> RenderRecord | None:
        row = self._conn.execute(
            "SELECT id, garment_id, garment_version, fabric_id, color, prompt, "
            "image_path, model_id, created_at FROM renders WHERE id = ?",
            (render_id,),
        ).fetchone()
        return self._row(row) if row else None

    def delete_for_garment(self, garment_id: str) -> list[str]:
        rows = self._conn.execute(
            "SELECT image_path FROM renders WHERE garment_id = ?", (garment_id,)
        ).fetchall()
        self._conn.execute("DELETE FROM renders WHERE garment_id = ?", (garment_id,))
        self._conn.commit()
        return [r[0] for r in rows]

    def close(self) -> None:
        self._conn.close()

    @staticmethod
    def _row(r: tuple) -> RenderRecord:
        return RenderRecord(
            id=r[0], garment_id=r[1], garment_version=r[2], fabric_id=r[3], color=r[4],
            prompt=r[5], image_path=r[6], model_id=r[7],
            created_at=datetime.fromisoformat(r[8]),
        )
