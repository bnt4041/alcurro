"""Resumen del día, proyecto en fichaje, tablas projects y clock_pending."""

import os
import sys

from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://hrm:hrm_secret@localhost:5432/hrm"
)


def column_exists(conn, table: str, column: str) -> bool:
    cols = [c["name"] for c in inspect(conn).get_columns(table)]
    return column in cols


def table_exists(conn, table: str) -> bool:
    return table in inspect(conn).get_table_names()


def main() -> None:
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        if not column_exists(conn, "clock_settings", "daily_summary_enabled"):
            conn.execute(
                text(
                    """
                    ALTER TABLE clock_settings
                    ADD COLUMN daily_summary_enabled BOOLEAN NOT NULL DEFAULT TRUE
                    """
                )
            )
            print("Columna clock_settings.daily_summary_enabled creada.")

        if not column_exists(conn, "clock_settings", "require_project_on_clock_in"):
            conn.execute(
                text(
                    """
                    ALTER TABLE clock_settings
                    ADD COLUMN require_project_on_clock_in BOOLEAN NOT NULL DEFAULT FALSE
                    """
                )
            )
            print("Columna clock_settings.require_project_on_clock_in creada.")

        if not table_exists(conn, "projects"):
            conn.execute(
                text(
                    """
                    CREATE TABLE projects (
                        id UUID PRIMARY KEY,
                        company_id UUID NOT NULL REFERENCES companies(id),
                        name VARCHAR(200) NOT NULL,
                        code VARCHAR(50) NOT NULL,
                        address VARCHAR(500),
                        planned_hours DOUBLE PRECISION,
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_projects_company ON projects (company_id)"
                )
            )
            conn.execute(
                text(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_projects_company_code
                    ON projects (company_id, code)
                    """
                )
            )
            print("Tabla projects creada.")

        if not table_exists(conn, "clock_pending_fichajes"):
            conn.execute(
                text(
                    """
                    CREATE TABLE clock_pending_fichajes (
                        employee_id UUID PRIMARY KEY REFERENCES employees(id),
                        record_type VARCHAR(20) NOT NULL,
                        latitude DOUBLE PRECISION,
                        longitude DOUBLE PRECISION,
                        whatsapp_message_id VARCHAR(100),
                        created_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
            print("Tabla clock_pending_fichajes creada.")

        if not column_exists(conn, "clock_ins", "project_id"):
            conn.execute(
                text(
                    """
                    ALTER TABLE clock_ins
                    ADD COLUMN project_id UUID REFERENCES projects(id)
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_clock_ins_project
                    ON clock_ins (project_id)
                    """
                )
            )
            print("Columna clock_ins.project_id creada.")

    print("Migración clock_settings v3 OK.")


if __name__ == "__main__":
    main()
