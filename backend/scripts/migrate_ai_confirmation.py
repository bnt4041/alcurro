"""Migración: añade clock_in_id a work_breaks y nuevos campos a clock_pending_fichajes."""

from __future__ import annotations

import os
import sys

# Asegurar que backend/app está en el path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import engine


def column_exists(conn, table: str, column: str) -> bool:
    import sqlalchemy as sa

    insp = sa.inspect(conn)
    cols = [c["name"] for c in insp.get_columns(table)]
    return column in cols


def run() -> None:
    with engine.begin() as conn:
        # 1. Añadir clock_in_id a work_breaks
        if not column_exists(conn, "work_breaks", "clock_in_id"):
            conn.exec_driver_sql(
                "ALTER TABLE work_breaks "
                "ADD COLUMN clock_in_id UUID REFERENCES clock_ins(id)"
            )
            conn.exec_driver_sql(
                "CREATE INDEX IF NOT EXISTS ix_work_breaks_clock_in_id "
                "ON work_breaks (clock_in_id)"
            )
            print("Columna work_breaks.clock_in_id creada.")

        # 2. Añadir pending_confirmation a clock_pending_fichajes
        if not column_exists(conn, "clock_pending_fichajes", "pending_confirmation"):
            conn.exec_driver_sql(
                "ALTER TABLE clock_pending_fichajes "
                "ADD COLUMN pending_confirmation BOOLEAN NOT NULL DEFAULT FALSE"
            )
            print("Columna clock_pending_fichajes.pending_confirmation creada.")

        # 3. Añadir pending_intent a clock_pending_fichajes
        if not column_exists(conn, "clock_pending_fichajes", "pending_intent"):
            conn.exec_driver_sql(
                "ALTER TABLE clock_pending_fichajes "
                "ADD COLUMN pending_intent VARCHAR(50)"
            )
            print("Columna clock_pending_fichajes.pending_intent creada.")

    print("Migración completada: confirmaciones IA y paradas→fichaje.")


if __name__ == "__main__":
    run()
