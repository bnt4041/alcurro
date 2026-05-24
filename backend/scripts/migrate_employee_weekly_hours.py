"""Columna weekly_hours en employees (turno rotativo/complejo)."""

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
        if not column_exists(conn, "employees", "weekly_hours"):
            conn.execute(
                text(
                    """
                    ALTER TABLE employees
                    ADD COLUMN weekly_hours DOUBLE PRECISION
                    """
                )
            )
            print("Columna employees.weekly_hours creada.")
        else:
            print("Columna employees.weekly_hours ya existe.")


if __name__ == "__main__":
    main()
