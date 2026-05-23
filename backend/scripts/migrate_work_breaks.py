"""Crea tabla work_breaks (paradas / descansos)."""

import os
import sys

from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://hrm:hrm_secret@localhost:5432/hrm"
)


def main() -> None:
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        if "work_breaks" not in inspect(conn).get_table_names():
            conn.execute(
                text(
                    """
                    CREATE TABLE work_breaks (
                        id UUID PRIMARY KEY,
                        employee_id UUID NOT NULL REFERENCES employees(id),
                        record_type VARCHAR(20) NOT NULL,
                        recorded_at TIMESTAMP NOT NULL,
                        source VARCHAR(50) NOT NULL DEFAULT 'panel',
                        notes VARCHAR(500),
                        whatsapp_message_id VARCHAR(100)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX ix_work_breaks_employee_id ON work_breaks (employee_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX ix_work_breaks_recorded_at ON work_breaks (recorded_at)"
                )
            )
            print("Tabla work_breaks creada.")
        else:
            print("Tabla work_breaks ya existe.")


if __name__ == "__main__":
    main()
