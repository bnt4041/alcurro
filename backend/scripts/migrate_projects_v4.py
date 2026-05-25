"""active_for_clock en proyectos + tabla inbound_pending_uploads."""

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
        if table_exists(conn, "projects") and not column_exists(
            conn, "projects", "active_for_clock"
        ):
            conn.execute(
                text(
                    """
                    ALTER TABLE projects
                    ADD COLUMN active_for_clock BOOLEAN NOT NULL DEFAULT TRUE
                    """
                )
            )
            conn.execute(
                text(
                    """
                    UPDATE projects
                    SET active_for_clock = is_active
                    WHERE active_for_clock IS DISTINCT FROM is_active
                    """
                )
            )
            print("Columna projects.active_for_clock creada.")

        if not table_exists(conn, "inbound_pending_uploads"):
            conn.execute(
                text(
                    """
                    CREATE TABLE inbound_pending_uploads (
                        employee_id UUID PRIMARY KEY REFERENCES employees(id),
                        file_path VARCHAR(500) NOT NULL,
                        filename VARCHAR(255) NOT NULL,
                        whatsapp_message_id VARCHAR(100),
                        created_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
            print("Tabla inbound_pending_uploads creada.")


if __name__ == "__main__":
    main()
