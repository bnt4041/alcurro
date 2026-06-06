"""Migración: añade columna pending_meta JSON a clock_pending_fichajes."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from sqlalchemy.engine import create_engine

from app.config import get_settings

DATABASE_URL = get_settings().database_url


def table_exists(conn, table_name: str) -> bool:
    result = conn.execute(
        text(
            "SELECT EXISTS ("
            "  SELECT FROM information_schema.tables"
            "  WHERE table_name = :t"
            ")"
        ),
        {"t": table_name},
    )
    return bool(result.scalar())


def column_exists(conn, table_name: str, column_name: str) -> bool:
    result = conn.execute(
        text(
            "SELECT EXISTS ("
            "  SELECT FROM information_schema.columns"
            "  WHERE table_name = :t AND column_name = :c"
            ")"
        ),
        {"t": table_name, "c": column_name},
    )
    return bool(result.scalar())


def main() -> None:
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        if not table_exists(conn, "clock_pending_fichajes"):
            print("Tabla clock_pending_fichajes no existe aún — nada que migrar.")
            return

        if column_exists(conn, "clock_pending_fichajes", "pending_meta"):
            print("Columna pending_meta ya existe — nada que migrar.")
            return

        conn.execute(
            text(
                "ALTER TABLE clock_pending_fichajes "
                "ADD COLUMN pending_meta JSON DEFAULT NULL"
            )
        )
        print("✅ Columna pending_meta añadida a clock_pending_fichajes.")


if __name__ == "__main__":
    main()
