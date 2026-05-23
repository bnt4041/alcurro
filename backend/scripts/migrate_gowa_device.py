"""Añade tenants.gowa_device_id para goWA v8 (multi-device por contenedor)."""

import os
import sys

from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://hrm:hrm@localhost:5432/hrm"
)


def column_exists(conn, table: str, column: str) -> bool:
    return column in {c["name"] for c in inspect(conn).get_columns(table)}


def main() -> None:
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        if not column_exists(conn, "tenants", "gowa_device_id"):
            conn.execute(
                text("ALTER TABLE tenants ADD COLUMN gowa_device_id VARCHAR(80)")
            )
            print("Columna tenants.gowa_device_id creada.")
        else:
            print("Columna tenants.gowa_device_id ya existe.")


if __name__ == "__main__":
    main()
