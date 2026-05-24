"""Columna rotating_shift en employees."""

import os
import sys

from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://hrm:hrm_secret@localhost:5432/hrm"
)


def column_exists(conn, table: str, column: str) -> bool:
    return column in {c["name"] for c in inspect(conn).get_columns(table)}


def main() -> None:
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        if not column_exists(conn, "employees", "rotating_shift"):
            conn.execute(
                text(
                    """
                    ALTER TABLE employees
                    ADD COLUMN rotating_shift BOOLEAN NOT NULL DEFAULT FALSE
                    """
                )
            )
            print("Columna employees.rotating_shift creada.")
        else:
            print("Columna employees.rotating_shift ya existe.")


if __name__ == "__main__":
    main()
