"""Bloques de horario en employees y company_id en document_deliveries."""

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
        if not column_exists(conn, "employees", "work_schedule_blocks"):
            conn.execute(
                text(
                    """
                    ALTER TABLE employees
                    ADD COLUMN work_schedule_blocks JSONB NOT NULL DEFAULT '[]'::jsonb
                    """
                )
            )
            print("Columna employees.work_schedule_blocks creada.")
        else:
            print("Columna employees.work_schedule_blocks ya existe.")

        if not column_exists(conn, "document_deliveries", "company_id"):
            conn.execute(
                text(
                    """
                    ALTER TABLE document_deliveries
                    ADD COLUMN company_id UUID REFERENCES companies(id)
                    """
                )
            )
            conn.execute(
                text(
                    """
                    UPDATE document_deliveries d
                    SET company_id = e.company_id
                    FROM employees e
                    WHERE d.employee_id = e.id AND d.company_id IS NULL
                    """
                )
            )
            print("Columna document_deliveries.company_id creada.")

        cols = {c["name"]: c for c in inspect(conn).get_columns("document_deliveries")}
        if cols.get("employee_id", {}).get("nullable") is False:
            conn.execute(
                text(
                    "ALTER TABLE document_deliveries ALTER COLUMN employee_id DROP NOT NULL"
                )
            )
            print("document_deliveries.employee_id ahora nullable.")


if __name__ == "__main__":
    main()
