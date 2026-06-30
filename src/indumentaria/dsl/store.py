"""Repositorio SQLite: snapshots (garment_version) + log de operaciones (operation).

Doble persistencia a propósito: snapshots para leer/undo/diff; log para trazar
la edición. La reconstrucción del snapshot usa load_garment (polimórfico).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from indumentaria.dsl.garment import load_garment
from indumentaria.dsl.operations import Operation
from indumentaria.dsl.versioning import GarmentVersion

_SCHEMA = """
CREATE TABLE IF NOT EXISTS garment_version (
  garment_id    TEXT NOT NULL,
  version       INTEGER NOT NULL,
  snapshot_json TEXT NOT NULL,
  op_id         TEXT NOT NULL,
  op_type       TEXT NOT NULL,
  created_at    TEXT NOT NULL,
  PRIMARY KEY (garment_id, version)
);
CREATE TABLE IF NOT EXISTS operation (
  op_id        TEXT PRIMARY KEY,
  garment_id   TEXT NOT NULL,
  type         TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at   TEXT NOT NULL
);
"""

_SELECT = (
    "SELECT garment_id, version, snapshot_json, op_id, op_type, created_at "
    "FROM garment_version"
)


class GarmentStore:
    def __init__(self, db_path: str | Path = "data/indumentaria.db") -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)

    def save_version(self, version: GarmentVersion, operation: Operation) -> None:
        if version.op_type != operation.op_type:
            raise ValueError(
                f"op_type incoherente: version={version.op_type!r} operation={operation.op_type!r}"
            )
        self._conn.execute(
            "INSERT INTO operation (op_id, garment_id, type, payload_json, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                version.op_id,
                version.garment_id,
                operation.op_type,
                operation.model_dump_json(),
                version.created_at.isoformat(),
            ),
        )
        self._conn.execute(
            "INSERT INTO garment_version "
            "(garment_id, version, snapshot_json, op_id, op_type, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                version.garment_id,
                version.version,
                version.snapshot.model_dump_json(),
                version.op_id,
                version.op_type,
                version.created_at.isoformat(),
            ),
        )
        self._conn.commit()

    def get_version(self, garment_id: str, version: int) -> GarmentVersion | None:
        row = self._conn.execute(
            f"{_SELECT} WHERE garment_id = ? AND version = ?",
            (garment_id, version),
        ).fetchone()
        return self._row_to_version(row) if row else None

    def get_head(self, garment_id: str) -> GarmentVersion | None:
        row = self._conn.execute(
            f"{_SELECT} WHERE garment_id = ? ORDER BY version DESC LIMIT 1",
            (garment_id,),
        ).fetchone()
        return self._row_to_version(row) if row else None

    def list_history(self, garment_id: str) -> list[GarmentVersion]:
        rows = self._conn.execute(
            f"{_SELECT} WHERE garment_id = ? ORDER BY version",
            (garment_id,),
        ).fetchall()
        return [self._row_to_version(r) for r in rows]

    def get_operations(self, garment_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT op_id, type, payload_json, created_at FROM operation "
            "WHERE garment_id = ? ORDER BY created_at, rowid",
            (garment_id,),
        ).fetchall()
        return [
            {
                "op_id": r[0],
                "type": r[1],
                "payload": json.loads(r[2]),
                "created_at": datetime.fromisoformat(r[3]),
            }
            for r in rows
        ]

    def list_garment_ids(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT garment_id, MAX(created_at) AS last FROM garment_version "
            "GROUP BY garment_id ORDER BY last DESC"
        ).fetchall()
        return [r[0] for r in rows]

    def delete_garment(self, garment_id: str) -> None:
        self._conn.execute("DELETE FROM garment_version WHERE garment_id = ?", (garment_id,))
        self._conn.execute("DELETE FROM operation WHERE garment_id = ?", (garment_id,))
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> GarmentStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @staticmethod
    def _row_to_version(row: tuple) -> GarmentVersion:
        return GarmentVersion(
            garment_id=row[0],
            version=row[1],
            snapshot=load_garment(json.loads(row[2])),
            op_id=row[3],
            op_type=row[4],
            created_at=datetime.fromisoformat(row[5]),
        )
