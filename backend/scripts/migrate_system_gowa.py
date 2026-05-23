"""Añade system_settings.gowa_device_id para WhatsApp compartido."""

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
        if not column_exists(conn, "system_settings", "gowa_device_id"):
            conn.execute(
                text(
                    "ALTER TABLE system_settings ADD COLUMN gowa_device_id VARCHAR(80)"
                )
            )
            print("Columna system_settings.gowa_device_id creada.")
        else:
            print("Columna system_settings.gowa_device_id ya existe.")

        # URL de envío: localhost no funciona desde el contenedor backend
        conn.execute(
            text(
                """
                UPDATE system_settings
                SET gowa_send_url = 'http://gowa:3000/send/message'
                WHERE gowa_send_url LIKE '%localhost%'
                   OR gowa_send_url LIKE '%127.0.0.1%'
                """
            )
        )


if __name__ == "__main__":
    main()
