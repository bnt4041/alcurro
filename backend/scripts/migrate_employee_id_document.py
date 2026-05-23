"""Añade employees.id_document (DNI/NIE) con índice único por empresa."""

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
        if not column_exists(conn, "employees", "id_document"):
            conn.execute(
                text(
                    "ALTER TABLE employees ADD COLUMN id_document VARCHAR(20)"
                )
            )
            print("Columna employees.id_document creada.")
        else:
            print("Columna employees.id_document ya existe.")

        conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_employee_id_document_company
                ON employees (company_id, id_document)
                WHERE id_document IS NOT NULL AND id_document <> ''
                """
            )
        )
        print("Índice uq_employee_id_document_company listo.")


if __name__ == "__main__":
    main()
